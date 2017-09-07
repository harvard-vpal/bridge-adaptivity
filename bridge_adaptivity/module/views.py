import logging
from lxml import etree

from django.contrib.auth.decorators import login_required
from django import forms
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from slumber.exceptions import HttpClientError

from api.backends.openedx import get_available_courses, get_content_provider
from bridge_lti import outcomes
from module.forms import ActivityForm
from module.mixins import CollectionIdToContext
from .models import Collection, Activity, SequenceItem, Log, Sequence

log = logging.getLogger(__name__)


@method_decorator(login_required, name='dispatch')
class CollectionList(ListView):
    model = Collection
    context_object_name = 'collections'
    paginate_by = 10
    ordering = ['id']

    def get_queryset(self):
        return Collection.objects.filter(owner=self.request.user)


@method_decorator(login_required, name='dispatch')
class CollectionCreate(CreateView):
    model = Collection
    fields = ['name', 'owner', 'threshold', 'metadata', 'strict_forward']

    def get_form(self):
        # FIXME(wowkalucky): improve 'unique_together' default validation message
        form = super(CollectionCreate, self).get_form()
        form.fields['owner'].initial = self.request.user
        form.fields['owner'].widget = forms.HiddenInput(attrs={'readonly': True})
        return form


@method_decorator(login_required, name='dispatch')
class CollectionDetail(DetailView):
    model = Collection
    context_object_name = 'collection'

    def get_context_data(self, **kwargs):
        context = super(CollectionDetail, self).get_context_data(**kwargs)
        context['render_fields'] = ['name', 'tags', 'difficulty', 'points', 'source_name']
        context['activities'] = Activity.objects.filter(collection=self.object)
        context['source_courses'] = self.get_content_courses()
        context['activity_form'] = ActivityForm(initial={
            'collection': self.object,
            'lti_consumer': get_content_provider(),
        })
        return context

    @staticmethod
    def get_content_courses():
        try:
            return get_available_courses()
        except HttpClientError:
            log.exception(
                "There are no active LTI Content Providers. Enable one by setting via Bridge admin site"
                "LtiConsumer.is_active=True."
            )
            return []


@method_decorator(login_required, name='dispatch')
class ActivityCreate(CollectionIdToContext, CreateView):
    model = Activity
    fields = ['name', 'tags', 'difficulty', 'points', 'source_launch_url', 'source_name', 'source_context_id']

    def form_valid(self, form):
        activity = form.save(commit=False)
        collection = Collection.objects.get(pk=self.kwargs.get('collection_id'))
        activity.collection = collection
        activity.lti_consumer = get_content_provider()
        activity.save()
        return super(ActivityCreate, self).form_valid(form)

    def get_success_url(self):
        return reverse('module:collection-detail', kwargs={'pk': self.kwargs.get('collection_id')})


@method_decorator(login_required, name='dispatch')
class ActivityUpdate(CollectionIdToContext, UpdateView):
    model = Activity
    context_object_name = 'activity'
    fields = ActivityCreate.fields


@method_decorator(login_required, name='dispatch')
class ActivityDelete(DeleteView):
    model = Activity

    def get_success_url(self):
        return reverse('module:collection-detail', kwargs={'pk': self.object.collection.id})


class SequenceItemDetail(DetailView):
    model = SequenceItem
    context_object_name = 'sequence_item'
    template_name = 'module/sequence_item.html'

    def get_context_data(self, **kwargs):
        context = super(SequenceItemDetail, self).get_context_data(**kwargs)
        context['sequence_items'] = SequenceItem.objects.filter(sequence=self.object.sequence)

        Log.objects.create(
            sequence_item=self.object,
            log_type=Log.OPENED
        )

        return context


def sequence_item_next(request, pk):
    sequence_item = get_object_or_404(SequenceItem, pk=pk)

    sequence_item_next = SequenceItem.objects.filter(
        sequence=sequence_item.sequence,
        position=sequence_item.position + 1
    ).first()

    if sequence_item_next is None:
        try:
            log.warning("Sequence position is: {}".format(sequence_item.position))
            activity = sequence_item.sequence.collection.activity_set.all()[sequence_item.position]
        except IndexError:
            sequence_item.sequence.completed = True
            sequence_item.sequence.save()
            # NOTE(wowkalucky): send Sequence outcome if completed
            send_composite_outcome(sequence_item.sequence)
            return redirect(reverse('module:sequence-complete', kwargs={'pk': sequence_item.sequence_id}))

        sequence_item_next = SequenceItem.objects.create(
            sequence=sequence_item.sequence,
            activity=activity,
            position=sequence_item.position + 1
        )

    return redirect(reverse('module:sequence-item', kwargs={'pk': sequence_item_next.id}))


class SequenceComplete(DetailView):
    model = Sequence
    template_name = 'module/sequence_complete.html'


def send_composite_outcome(sequence):
    """
    Calculate and transmit the score for sequence.
    """
    # NOTE(wowkalucky): some advanced score calculation may be placed here
    score = sequence.total_points

    outcomes.send_score_update(sequence, score)


class LtiError(Exception):
    pass


def parse_grade_xml_body(body):
    """
    Parses values from the Outcome Service XML.

    XML body should contain nsmap with namespace, that is specified in LTI specs.

    Arguments:
        body (str): XML Outcome Service request body

    Returns:
        tuple: imsx_messageIdentifier, sourcedId, score, action

    Raises:
        LtiError
            if submitted score is outside the permitted range
            if the XML is missing required entities
            if there was a problem parsing the XML body
    """
    lti_spec_namespace = "http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0"
    namespaces = {'def': lti_spec_namespace}
    data = body.strip().encode('utf-8')

    try:
        parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')  # pylint: disable=no-member
        root = etree.fromstring(data, parser=parser)  # pylint: disable=no-member
    except etree.XMLSyntaxError as ex:
        raise (ex.message or 'Body is not valid XML')

    try:
        imsx_message_identifier = root.xpath("//def:imsx_messageIdentifier", namespaces=namespaces)[0].text or ''
    except IndexError:
        raise LtiError('Failed to parse imsx_messageIdentifier from XML request body')

    try:
        body = root.xpath("//def:imsx_POXBody", namespaces=namespaces)[0]
    except IndexError:
        raise LtiError('Failed to parse imsx_POXBody from XML request body')

    try:
        action = body.getchildren()[0].tag.replace('{' + lti_spec_namespace + '}', '')
    except IndexError:
        raise LtiError('Failed to parse action from XML request body')

    try:
        sourced_id = root.xpath("//def:sourcedId", namespaces=namespaces)[0].text
    except IndexError:
        raise LtiError('Failed to parse sourcedId from XML request body')

    try:
        score = root.xpath("//def:textString", namespaces=namespaces)[0].text
    except IndexError:
        raise LtiError('Failed to parse score textString from XML request body')

    # Raise exception if score is not float or not in range 0.0-1.0 regarding spec.
    score = float(score)
    if not 0.0 <= score <= 1.0:
        raise LtiError('score value outside the permitted range of 0.0-1.0')

    return imsx_message_identifier, sourced_id, score, action


@csrf_exempt
def sequence_item_grade(request):
    imsx_message_identifier, sourced_id, score, action = parse_grade_xml_body(request.body)
    log.warning("msg identifier: {}, scourced_id: {}, score: {}, action: {}".format(imsx_message_identifier, sourced_id, score, action))
