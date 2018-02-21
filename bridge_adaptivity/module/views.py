import logging
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.http import HttpResponse, HttpResponseNotFound
from django.http.response import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.views.generic.edit import FormView
from lti import InvalidLTIConfigError, OutcomeRequest, OutcomeResponse
from lti.outcome_response import CODE_MAJOR_CODES, SEVERITY_CODES
from slumber.exceptions import HttpClientError

from api.backends.openedx import get_available_courses, get_content_provider
from module import tasks, utils
from module.base_views import BaseCollectionView, BaseCourseView, BaseGroupView
from module.forms import ActivityForm, BaseGradingPolicyForm, GroupForm
from module.mixins.views import (
    CollectionIdToContextMixin, GroupEditFormMixin, LtiSessionMixin, OnlyMyObjectsMixin, SetUserInFormMixin
)
from module.models import (
    Activity, Collection, CollectionGroup, GRADING_POLICY_NAME_TO_CLS, Log, Sequence, SequenceItem
)

log = logging.getLogger(__name__)


@method_decorator(login_required, name='dispatch')
class CourseCreate(BaseCourseView, SetUserInFormMixin, CreateView):
    fields = 'owner', 'name', 'description'


@method_decorator(login_required, name='dispatch')
class CourseList(BaseCourseView, ListView):
    context_object_name = 'courses'


@method_decorator(login_required, name='dispatch')
class CourseDetail(BaseCourseView, DetailView):
    context_object_name = 'course'


@method_decorator(login_required, name='dispatch')
class CourseUpdate(BaseCourseView, SetUserInFormMixin, UpdateView):
    fields = 'name', 'description'
    context_object_name = 'course'

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        response = super(CourseUpdate, self).form_valid(form)
        self.object.owner = self.request.user
        return response


@method_decorator(login_required, name='dispatch')
class CourseDelete(BaseCourseView, GroupEditFormMixin, DeleteView):
    def get_success_url(self):
        return reverse('module:course-list')

    def get(self, *args, **kwargs):
        return self.post(*args, **kwargs)


@method_decorator(login_required, name='dispatch')
class GroupList(OnlyMyObjectsMixin, ListView):
    model = CollectionGroup
    context_object_name = 'groups'
    ordering = ['slug']


class GetGradingPolicyForm(FormView):
    form_class = BaseGradingPolicyForm
    template_name = 'module/gradingpolicy_form.html'
    prefix = 'grading'

    def get_form_class(self):
        policy_cls = GRADING_POLICY_NAME_TO_CLS.get(self.request.GET.get('grading_policy'), None)
        if policy_cls is None:
            raise Http404("No such grading policy")
        return policy_cls.get_form_class()

    def get_form_kwargs(self):
        kwargs = super(GetGradingPolicyForm, self).get_form_kwargs()
        if self.kwargs.get('group_slug'):
            group = CollectionGroup.objects.filter(
                slug=self.kwargs.get('group_slug'),
                grading_policy__name=self.request.GET.get('grading_policy')
            ).first()
            if group:
                kwargs['instance'] = group.grading_policy
        return kwargs

    def get_form(self, form_class=None):
        self.form_class = self.get_form_class()
        form = super(GetGradingPolicyForm, self).get_form()
        gp = self.request.GET.get('grading_policy')
        if gp in GRADING_POLICY_NAME_TO_CLS:
            form.fields['name'].initial = self.request.GET.get('grading_policy')
            return form
        else:
            raise Http404()


@method_decorator(login_required, name='dispatch')
class GroupCreate(BaseGroupView, SetUserInFormMixin, GroupEditFormMixin, CreateView):
    pass


@method_decorator(login_required, name='dispatch')
class GroupDetail(BaseGroupView, DetailView):
    context_object_name = 'group'

    def get_context_data(self, **kwargs):
        context = super(GroupDetail, self).get_context_data(**kwargs)
        context.update({'bridge_host': settings.BRIDGE_HOST})
        return context


@method_decorator(login_required, name='dispatch')
class GroupUpdate(BaseGroupView, SetUserInFormMixin, GroupEditFormMixin, UpdateView):
    form_class = GroupForm
    context_object_name = 'group'

    def get_success_url(self):
        return self.object.get_absolute_url()


@method_decorator(login_required, name='dispatch')
class GroupDelete(BaseGroupView, DeleteView):
    def get_success_url(self):
        return reverse('module:group-list')

    def get(self, *args, **kwargs):
        return self.post(*args, **kwargs)


class CollectionList(BaseCollectionView, ListView):
    context_object_name = 'collections'


@method_decorator(login_required, name='dispatch')
class CollectionCreate(BaseCollectionView, SetUserInFormMixin, CreateView):
    pass


@method_decorator(login_required, name='dispatch')
class CollectionUpdate(BaseCollectionView, SetUserInFormMixin, UpdateView):
    def get_success_url(self):
        return reverse('module:collection-detail', kwargs={'pk': self.kwargs.get('pk')})


@method_decorator(login_required, name='dispatch')
class CollectionDetail(BaseCollectionView, DetailView):
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
        context['sync_available'] = self.object.collection_groups.exists()
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


@method_decorator(login_required, name='dispatch')
class CollectionDelete(DeleteView):
    model = Collection

    def get_success_url(self):
        return reverse('module:collection-list')

    def get_queryset(self):
        return super(CollectionDelete, self).get_queryset().filter(owner=self.request.user)

    def get(self, *args, **kwargs):
        return self.post(*args, **kwargs)


@method_decorator(login_required, name='dispatch')
class ActivityCreate(CollectionIdToContextMixin, CreateView):
    model = Activity
    fields = [
        'name', 'tags', 'atype', 'difficulty', 'points', 'source_launch_url',
        'source_name', 'source_context_id', 'stype',
    ]

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
    next_forbidden = (
        sequence_item.is_problem and
        sequence_item.position == last_item and
        sequence_item.sequence.collection.strict_forward and
        sequence_item.score is None
    )
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
            sequence = sequence_item.sequence
            policy = sequence.group.grading_policy.policy_instance(
                sequence=sequence, user_id=sequence.lti_user.user_id,
            )
            policy.send_grade()
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
    log.debug("New Log is created log_type: 'Submitted', attempt: {}, correct: {}, sequence is completed: {}".format(
        attempt, correct, sequence_item.sequence.completed
    ))

    sequence = sequence_item.sequence
    if sequence.lis_result_sourcedid:
        policy = sequence.group.grading_policy.policy_instance(sequence=sequence, request=request, user_id=user_id)
        policy.send_grade()

    return HttpResponse(xml, content_type="application/xml")


def sync_collection(request, pk):
    """
    Synchronize collection immediately.
    """
    back_url = request.GET.get('back_url')
    collection = get_object_or_404(Collection, pk=pk)
    collection.save()
    log.debug("Immediate sync task is created, time: {}".format(collection.updated_at))
    tasks.sync_collection_engines.delay(
        collection_id=pk, created_at=collection.updated_at
    )
    return redirect(reverse('module:collection-detail', kwargs={'pk': pk}) + '?back_url={}'.format(back_url))
