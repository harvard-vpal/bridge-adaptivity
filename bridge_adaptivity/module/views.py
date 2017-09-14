import json
import logging
from xml.sax.saxutils import escape

from django.http import HttpResponseNotFound, HttpResponse

from django.contrib.auth.decorators import login_required
from django import forms
from django.db.models import Sum, Count, Max
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from slumber.exceptions import HttpClientError

from api.backends.openedx import get_available_courses, get_content_provider
from bridge_lti import outcomes
from bridge_lti.outcomes import calculate_grade
from module import ENGINE
from module.forms import ActivityForm
from module.mixins import CollectionIdToContextMixin, LtiSessionMixin
from module.models import Collection, Activity, SequenceItem, Log, Sequence
from module import utils
from module.utils import BridgeError

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
        activities = Activity.objects.filter(collection=self.object)
        context = super(CollectionDetail, self).get_context_data(**kwargs)
        context['render_fields'] = ['name', 'tags', 'difficulty', 'points', 'source']
        context['activities'] = activities
        context['source_courses'] = self.get_content_courses()
        context['activity_form'] = ActivityForm(initial={
            'collection': self.object,
            'lti_consumer': get_content_provider(),
        })
        context['activities_data'] = json.dumps([{
            'name': activity.name,
            'source_launch_url': activity.source_launch_url,
        } for activity in activities])
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
class ActivityCreate(CollectionIdToContextMixin, CreateView):
    model = Activity
    fields = ['name', 'tags', 'atype', 'difficulty', 'points', 'source_launch_url', 'source_name', 'source_context_id']

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
class ActivityUpdate(CollectionIdToContextMixin, UpdateView):
    model = Activity
    context_object_name = 'activity'
    fields = ActivityCreate.fields

    def get(self, request, *args, **kwargs):
        activity = self.get_object()
        if 'direction' in kwargs:
            try:
                # NOTE(wowkalucky): expects 'up', 'down' (also possible: 'top', 'bottom')
                getattr(activity, kwargs['direction'])()
            except AttributeError:
                log.exception("Unknown ordering method!")
            return redirect(reverse('module:collection-detail', kwargs={'pk': activity.collection.id}))

        return super(ActivityUpdate, self).get(request, *args, **kwargs)


@method_decorator(login_required, name='dispatch')
class ActivityDelete(DeleteView):
    model = Activity

    def get_success_url(self):
        return reverse('module:collection-detail', kwargs={'pk': self.object.collection.id})


class SequenceItemDetail(LtiSessionMixin, DetailView):
    model = SequenceItem
    context_object_name = 'sequence_item'
    template_name = 'module/sequence_item.html'

    def get_context_data(self, **kwargs):
        context = super(SequenceItemDetail, self).get_context_data(**kwargs)
        item_filter = {'sequence': self.object.sequence}
        if self.request.session.get('Lti_update_activity'):
            item_filter.update({'score__isnull': False})
        context['sequence_items'] = SequenceItem.objects.filter(**item_filter)

        Log.objects.create(
            sequence_item=self.object,
            log_type=Log.OPENED
        )

        return context


def sequence_item_next(request, pk):
    try:
        sequence_item = SequenceItem.objects.get(pk=pk)
    except SequenceItem.DoesNotExist:
        log.exception("SequenceItem which supposed to exist can't be found!")
        return render(
            request,
            template_name="bridge_lti/announcement.html",
            context={
                'title': 'Something went wrong...',
                'message': 'Internal problem was occurred, please, inform course personal about your experience.',
                'tip': "ERROR: next sequence item can't be proposed",
            }
        )
    last_item = SequenceItem.objects.filter(
        sequence=sequence_item.sequence
    ).aggregate(last_item=Max('position'))['last_item']
    next_sequence_item = SequenceItem.objects.filter(
        sequence=sequence_item.sequence,
        position=sequence_item.position + 1
    ).first()
    log.debug("Picked next sequence item is: {}".format(next_sequence_item))

    if not next_sequence_item or next_sequence_item.position == last_item:
        activity = utils.chose_activity(sequence_item)
        if next_sequence_item is None:
            if not activity:
                return redirect(reverse('module:sequence-complete', kwargs={'pk': sequence_item.sequence_id}))
            next_sequence_item = SequenceItem.objects.create(
                sequence=sequence_item.sequence,
                activity=activity,
                position=sequence_item.position + 1
            )
        elif request.session.pop('Lti_update_activity', None):
            log.debug('Bridge updates activity in the un-submitted SequenceItem')
            if activity:
                next_sequence_item.activity = activity
                next_sequence_item.save()
    return redirect(reverse('module:sequence-item', kwargs={'pk': next_sequence_item.id}))


class SequenceComplete(LtiSessionMixin, DetailView):
    model = Sequence
    template_name = 'module/sequence_complete.html'


def send_composite_outcome(sequence):
    """
    Calculate and transmit the score for sequence.
    """
    threshold = sequence.collection.threshold
    items_result = sequence.items.aggregate(points_earned=Sum('score'), trials_count=Count('score'))

    score = calculate_grade(items_result['trials_count'], threshold, items_result['points_earned'])

    outcomes.send_score_update(sequence, score)
    return score


@csrf_exempt
def callback_sequence_item_grade(request):
    failure = {
        'imsx_codeMajor': 'failure',
        'imsx_messageIdentifier': 'unknown',
        'response': ''
    }
    try:
        imsx_message_identifier, sourced_id, score, action = utils.parse_callback_grade_xml(request.body)
    except BridgeError as err:
        body = escape(request.body) if request.body else ''
        error_message = "Request body XML parsing error: {} {}".format(err.message, body)
        log.debug("Failure to archive grade from the source: %s" + error_message)
        failure.update({'imsx_description': error_message})
        return HttpResponse(utils.XML.format(**failure), content_type='application/xml')
    sequence_item_id, user_id, _ = sourced_id.split(':')
    if action == 'replaceResultRequest':
        success = {
            'imsx_codeMajor': 'success',
            'imsx_description': 'Score for {sourced_id} is now {score}'.format(sourced_id=sourced_id, score=score),
            'imsx_messageIdentifier': escape(imsx_message_identifier),
            'response': '<replaceResultResponse/>'
        }
        log.debug("[LTI]: Grade is saved.")
        xml = utils.XML.format(**success)
    log.debug("Received CallBack with the submitted answer for sequence item {}.".format(sequence_item_id))
    try:
        sequence_item = SequenceItem.objects.get(id=sequence_item_id)
    except SequenceItem.DoesNotExist:
        error_message = "Sequence Item with the ID={} was not found".format(sequence_item_id)
        failure.update({'imsx_description': error_message})
        log.debug("Grade cannot be updated: SequenceItem is not found.")
        return HttpResponseNotFound(utils.XML.format(**failure), content_type='application/xml')
    sequence_item.score = float(score)
    sequence_item.save()
    log.debug("Sequence item {} grade is updated".format(sequence_item))
    last_log_submit = Log.objects.filter(sequence_item=sequence_item, log_type='S').last()
    attempt = (last_log_submit.attempt if last_log_submit else 0) + 1
    correct = bool(score)
    Log.objects.create(
        sequence_item=sequence_item,
        log_type=Log.SUBMITTED,
        answer=correct,
        attempt=attempt,
    )
    log.debug("New Log is created log_type: 'Submitted', attempt: {}, correct: {}".format(attempt, correct))
    ENGINE.submit_activity_answer(sequence_item)
    log.debug("Adaptive engine is updated with the student {} answer on the activity {}".format(
        user_id, sequence_item.activity.name
    ))
    sequence = sequence_item.sequence
    if sequence.lis_result_sourcedid:
        grade = send_composite_outcome(sequence)
        log.debug("Send updated grade {} to the LMS, for the student {}".format(grade, user_id))
    return HttpResponse(xml, content_type="application/xml")
