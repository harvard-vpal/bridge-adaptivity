import logging
from xml.sax.saxutils import escape

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from lti import InvalidLTIConfigError, OutcomeRequest, OutcomeResponse
from lti.outcome_response import CODE_MAJOR_CODES, SEVERITY_CODES
from slumber.exceptions import HttpClientError

from api.backends.openedx import get_available_courses, get_content_provider
from bridge_lti.outcomes import update_lms_grades
from module import utils
from module.forms import ActivityForm
from module.mixins import CollectionIdToContextMixin, CollectionMixin, GroupEditFormMixin, LtiSessionMixin
from module.models import Activity, Collection, CollectionGroup, Log, Sequence, SequenceItem


log = logging.getLogger(__name__)


@method_decorator(login_required, name='dispatch')
class GroupList(ListView):
    model = CollectionGroup
    context_object_name = 'groups'
    ordering = ['slug']

    def get_queryset(self):
        return self.model.objects.filter(owner=self.request.user)


@method_decorator(login_required, name='dispatch')
class GroupCreate(GroupEditFormMixin, CreateView):
    model = CollectionGroup
    slug_field = 'slug'
    slug_url_kwarg = 'group_slug'
    fields = [
        'name', 'owner', 'collections', 'engine'
    ]


@method_decorator(login_required, name='dispatch')
class GroupDetail(DetailView):
    model = CollectionGroup
    slug_field = 'slug'
    slug_url_kwarg = 'group_slug'
    context_object_name = 'group'

    def get_queryset(self):
        return CollectionGroup.objects.filter(owner=self.request.user)


@method_decorator(login_required, name='dispatch')
class GroupUpdate(GroupEditFormMixin, UpdateView):
    model = CollectionGroup
    slug_field = 'slug'
    slug_url_kwarg = 'group_slug'
    fields = [
        'name', 'owner', 'collections', 'engine'
    ]

    context_object_name = 'group'

    def get_success_url(self):
        return reverse('module:group-detail', kwargs={'pk': self.kwargs.get('pk')})


@method_decorator(login_required, name='dispatch')
class CollectionList(CollectionMixin, ListView):
    model = Collection
    context_object_name = 'collections'
    ordering = ['id']


@method_decorator(login_required, name='dispatch')
class CollectionCreate(CollectionMixin, CreateView):
    model = Collection
    fields = ['name', 'owner', 'threshold', 'metadata', 'correctness_matters', 'strict_forward']

    def get_form(self):
        # FIXME(wowkalucky): improve 'unique_together' default validation message
        form = super(CollectionCreate, self).get_form()
        form.fields['owner'].initial = self.request.user
        form.fields['owner'].widget = forms.HiddenInput(attrs={'readonly': True})
        return form


@method_decorator(login_required, name='dispatch')
class CollectionUpdate(CollectionMixin, UpdateView):
    model = Collection
    fields = ['name', 'threshold', 'metadata', 'strict_forward', 'correctness_matters']

    def get_success_url(self):
        return reverse('module:collection-detail', kwargs={'pk': self.kwargs.get('pk')})


@method_decorator(login_required, name='dispatch')
class CollectionDetail(CollectionMixin, DetailView):
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
        context['launch_url'] = self.get_launch_url()
        engine_failure = self.request.GET.get('engine')
        if engine_failure:
            context['engine'] = engine_failure
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

    def get_launch_url(self):
        """
        Build LTI launch URL for the Collection to be used by LTI Tool.

        Example: https://bridge.host/lti/launch/3
        :return: launch URL
        """
        # NOTE(idegtiarov) Improve creation of the launch URL
        return '{bridge_host}/lti/launch/{collection_id}'.format(
            bridge_host=settings.BRIDGE_HOST, collection_id=self.object.id
        )


@method_decorator(login_required, name='dispatch')
class ActivityCreate(CollectionIdToContextMixin, CreateView):
    model = Activity
    fields = ['name', 'tags', 'atype', 'difficulty', 'points', 'source_launch_url', 'source_name', 'source_context_id']

    def form_valid(self, form):
        activity = form.save(commit=False)
        collection = Collection.objects.get(pk=self.kwargs.get('collection_id'))
        activity.collection = collection
        activity.lti_consumer = get_content_provider()
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

    def delete(self, request, *args, **kwargs):
        try:
            return super(ActivityDelete, self).delete(request, *args, **kwargs)
        except (ValidationError, TypeError):
            return redirect("{}?engine=failure".format(self.get_success_url()))


class SequenceItemDetail(LtiSessionMixin, DetailView):
    model = SequenceItem
    context_object_name = 'sequence_item'
    template_name = 'module/sequence_item.html'

    def get_context_data(self, **kwargs):
        context = super(SequenceItemDetail, self).get_context_data(**kwargs)
        item_filter = {'sequence': self.object.sequence}
        if self.request.session.get('Lti_update_activity') and self.object.sequence.items.all().count() > 1:
            item_filter.update({'score__isnull': False})
        if self.request.GET.get('forbidden'):
            context['forbidden'] = True
        context['sequence_items'] = SequenceItem.objects.filter(**item_filter)
        log.debug("Sequence Items on the page: {}".format(context['sequence_items'].count()))

        Log.objects.create(
            sequence_item=self.object,
            log_type=Log.OPENED
        )

        return context


def _check_next_forbidden(pk):
    """
    Check if next sequence item is forbidden to be shown to the student.

    :param pk: currently opened SequenseItem's pk
    :return: tuple of the parameters next_forbidden, last_item, sequence_item
             Where next_forbidden is boolean flag to forbid show next sequence item to the student,
             last_item (integer) is index of the last SequenceItem,
             sequence_item (SequenceItem inctance) of the currently open sequence item
    """
    sequence_item = SequenceItem.objects.get(pk=pk)

    last_item = SequenceItem.objects.filter(
        sequence=sequence_item.sequence
    ).aggregate(last_item=Max('position'))['last_item']
    next_forbidden = False
    if (
        sequence_item.position == last_item and
        sequence_item.sequence.collection.strict_forward and
        sequence_item.score is None
    ):
        next_forbidden = True
    log.debug("Next item is forbidden: {}".format(next_forbidden))
    return next_forbidden, last_item, sequence_item


def sequence_item_next(request, pk):
    try:
        next_forbidden, last_item, sequence_item = _check_next_forbidden(pk)
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
    if next_forbidden:
        return redirect("{}?forbidden=true".format(reverse('module:sequence-item', kwargs={'pk': sequence_item.id})))
    next_sequence_item = SequenceItem.objects.filter(
        sequence=sequence_item.sequence,
        position=sequence_item.position + 1
    ).first()
    log.debug("Picked next sequence item is: {}".format(next_sequence_item))

    if not next_sequence_item or next_sequence_item.position == last_item:
        activity = utils.choose_activity(sequence_item)
        update_activity = request.session.pop('Lti_update_activity', None)
        if next_sequence_item is None:
            if not activity:
                return redirect(reverse('module:sequence-complete', kwargs={'pk': sequence_item.sequence_id}))
            next_sequence_item = SequenceItem.objects.create(
                sequence=sequence_item.sequence,
                activity=activity,
                position=sequence_item.position + 1
            )
        elif update_activity:
            log.debug('Bridge updates activity in the un-submitted SequenceItem')
            if activity:
                next_sequence_item.activity = activity
                next_sequence_item.save()
    return redirect(reverse('module:sequence-item', kwargs={'pk': next_sequence_item.id}))


class SequenceComplete(LtiSessionMixin, DetailView):
    model = Sequence
    template_name = 'module/sequence_complete.html'


@csrf_exempt
def callback_sequence_item_grade(request):
    outcome_response = OutcomeResponse(
        message_identifier='unknown', code_major=CODE_MAJOR_CODES[2], severity=SEVERITY_CODES[0]
    )

    try:
        outcome_request = OutcomeRequest().from_post_request(request)
        score = float(outcome_request.score)
        if not 0.0 <= score <= 1.0:
            raise InvalidLTIConfigError('[LTI] score value is outside the permitted range of 0.0-1.0')
        operation = outcome_request.operation
        if not operation == 'replaceResult':
            raise InvalidLTIConfigError('[LTI] request operation {} cannot be proceed'.format(operation))
    except (InvalidLTIConfigError, ValueError) as err:
        body = escape(request.body) if request.body else ''
        error_message = "Request body XML parsing error: {} {}".format(err.message, body)
        log.debug("Failure to archive grade from the source: %s" + error_message)
        outcome_response.description = escape(error_message)
        return HttpResponse(outcome_response.generate_response_xml(), content_type='application/xml')
    sequence_item_id, user_id, _ = outcome_request.lis_result_sourcedid.text.split(':')
    outcome_response.code_major = CODE_MAJOR_CODES[0]
    outcome_response.description = 'Score for {sourced_id} is now {score}'.format(
        sourced_id=outcome_request.lis_result_sourcedid, score=score
    )
    outcome_response.message_identifier = outcome_request.message_identifier
    outcome_response.operation = operation

    xml = outcome_response.generate_response_xml()
    log.debug("Received CallBack with the submitted answer for sequence item {}.".format(sequence_item_id))
    try:
        sequence_item = SequenceItem.objects.get(id=sequence_item_id)
    except SequenceItem.DoesNotExist:
        error_message = "Sequence Item with the ID={} was not found".format(sequence_item_id)
        outcome_response.description = escape(error_message)
        log.debug("[LTI] {}".format(error_message))
        return HttpResponseNotFound(outcome_response.generate_response_xml(), content_type='application/xml')

    sequence_item.score = score
    sequence_item.save()
    log.debug("[LTI] Sequence item {} grade is updated".format(sequence_item))
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

    sequence = sequence_item.sequence
    if sequence.lis_result_sourcedid:
        update_lms_grades(request, sequence, user_id)

    return HttpResponse(xml, content_type="application/xml")
