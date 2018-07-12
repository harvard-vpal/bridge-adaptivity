import logging
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.http import HttpResponse, HttpResponseNotFound
from django.http.response import Http404
from django.shortcuts import get_list_or_404, get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.views.generic.edit import FormView
from lti import InvalidLTIConfigError, OutcomeRequest, OutcomeResponse
from lti.outcome_response import CODE_MAJOR_CODES, SEVERITY_CODES
from slumber.exceptions import HttpClientError

from api.backends.api_client import get_available_courses
from module import tasks, utils
from module.base_views import BaseCollectionView, BaseCourseView, BaseGroupView
from module.forms import ActivityForm, AddCollectionGroupForm, AddCourseGroupForm, BaseGradingPolicyForm, GroupForm
from module.mixins.views import (
    BackURLMixin, CollectionSlugToContextMixin, GroupEditFormMixin, JsonResponseMixin, LinkObjectsMixin,
    LtiSessionMixin, ModalFormMixin, OnlyMyObjectsMixin, SetUserInFormMixin
)
from module.models import (
    Activity, Collection, CollectionGroup, Course, GRADING_POLICY_NAME_TO_CLS, Log, Sequence, SequenceItem
)

log = logging.getLogger(__name__)


@method_decorator(login_required, name='dispatch')
class CourseCreate(BaseCourseView, SetUserInFormMixin, ModalFormMixin, CreateView):
    fields = 'owner', 'name', 'description'


@method_decorator(login_required, name='dispatch')
class CourseList(BaseCourseView, ListView):
    context_object_name = 'courses'


@method_decorator(login_required, name='dispatch')
class CourseDetail(LinkObjectsMixin, BaseCourseView, DetailView):
    context_object_name = 'course'
    link_form_class = AddCourseGroupForm
    link_object_name = 'group'

    def get_link_form_kwargs(self):
        return dict(user=self.request.user, course=self.object)

    def get_link_action_url(self):
        return reverse('module:group-add')

    def get_has_available_objects(self, form):
        return form.fields['groups'].queryset.exists()


@method_decorator(login_required, name='dispatch')
class CourseUpdate(BaseCourseView, SetUserInFormMixin, ModalFormMixin, UpdateView):
    fields = 'name', 'description'
    context_object_name = 'course'

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.owner = self.request.user
        return response


@method_decorator(login_required, name='dispatch')
class CourseDelete(BaseCourseView, GroupEditFormMixin, DeleteView):
    def get_success_url(self):
        return self.request.GET.get('return_url') or reverse('module:course-list')

    def get(self, *args, **kwargs):
        return self.post(*args, **kwargs)


@method_decorator(login_required, name='dispatch')
class CourseAddGroup(JsonResponseMixin, FormView):
    template_name = 'module/modals/course_add_group.html'
    form_class = AddCourseGroupForm

    def get_success_url(self):
        return self.request.GET.get('return_url') or reverse('module:course-detail', kwargs=self.kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['course'] = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        return kwargs


@method_decorator(login_required, name='dispatch')
class CourseRmGroup(UpdateView):
    model = CollectionGroup
    template_name = 'module/modals/course_add_group.html'
    slug_url_kwarg = 'group_slug'
    fields = ('course',)

    def get_queryset(self):
        qs = super().get_queryset()
        course = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        qs.filter(
            owner=self.request.user,
            course=course,
        )
        return qs

    def get_success_url(self):
        return (
            self.request.GET.get('return_url') or
            reverse('module:course-detail', kwargs={'course_slug': self.kwargs['course_slug']})
        )

    def get(self, *args, **kwargs):
        self.object = self.get_object(self.get_queryset())
        self.object.course = None
        self.object.save()
        return redirect(self.get_success_url())


@method_decorator(login_required, name='dispatch')
class GroupList(OnlyMyObjectsMixin, ListView):
    model = CollectionGroup
    context_object_name = 'groups'
    ordering = ['slug']


@method_decorator(login_required, name='dispatch')
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
        kwargs = super().get_form_kwargs()
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
        form = super().get_form()
        gp = self.request.GET.get('grading_policy')
        if gp in GRADING_POLICY_NAME_TO_CLS:
            form.fields['name'].initial = self.request.GET.get('grading_policy')
            return form
        else:
            raise Http404()


@method_decorator(login_required, name='dispatch')
class GroupCreate(BaseGroupView, SetUserInFormMixin, GroupEditFormMixin, ModalFormMixin, CreateView):

    def form_valid(self, form):
        result = super().form_valid(form)
        if 'course_slug' in self.kwargs and self.kwargs['course_slug']:
            Course.objects.get(slug=self.kwargs['course_slug']).course_groups.add(self.object)
        return result


@method_decorator(login_required, name='dispatch')
class GroupDetail(LinkObjectsMixin, BaseGroupView, DetailView):
    context_object_name = 'group'
    link_form_class = AddCollectionGroupForm
    link_object_name = 'collection'

    def get_link_form_kwargs(self):
        return dict(user=self.request.user, group=self.object)

    def get_link_action_url(self):
        return reverse('module:collection-add')

    def get_has_available_objects(self, form):
        return form.fields['collections'].queryset.exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'bridge_host': settings.BRIDGE_HOST,
            'grade_update_available': self.object.sequence_set.exists(),
        })
        return context


class AddCollectionInGroup(JsonResponseMixin, FormView):
    template_name = 'module/modals/course_add_group.html'
    form_class = AddCollectionGroupForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['group'] = get_object_or_404(CollectionGroup, slug=self.kwargs.get('group_slug'))
        return kwargs

    def get_success_url(self):
        return reverse('module:group-detail', kwargs=self.kwargs)


@method_decorator(login_required, name='dispatch')
class GroupUpdate(BaseGroupView, SetUserInFormMixin, GroupEditFormMixin, ModalFormMixin, UpdateView):
    form_class = GroupForm
    context_object_name = 'group'


@method_decorator(login_required, name='dispatch')
class GroupDelete(BaseGroupView, DeleteView):
    def get_success_url(self):
        return self.request.GET.get('return_url') or reverse('module:group-list')

    def get(self, *args, **kwargs):
        return self.post(*args, **kwargs)


@method_decorator(login_required, name='dispatch')
class CollectionList(BaseCollectionView, ListView):
    context_object_name = 'collections'


@method_decorator(login_required, name='dispatch')
class CollectionCreate(BaseCollectionView, SetUserInFormMixin, ModalFormMixin, CreateView):

    def form_valid(self, form):
        result = super().form_valid(form)
        if self.kwargs.get('group_slug'):
            CollectionGroup.objects.get(slug=self.kwargs['group_slug']).collections.add(self.object)
        return result


@method_decorator(login_required, name='dispatch')
class CollectionUpdate(BaseCollectionView, SetUserInFormMixin, ModalFormMixin, UpdateView):
    pass


@method_decorator(login_required, name='dispatch')
class CollectionDetail(BaseCollectionView, DetailView):
    context_object_name = 'collection'

    def get_context_data(self, **kwargs):
        activities = Activity.objects.filter(collection=self.object)
        context = super().get_context_data(**kwargs)
        context['render_fields'] = ['name', 'tags', 'difficulty', 'points', 'source']
        context['activities'] = activities
        context['source_courses'] = self.get_content_courses()
        context['activity_form'] = ActivityForm(initial={'collection': self.object})
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
        return self.request.GET.get('return_url') or reverse('module:collection-list')

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)

    # TODO check it
    def get(self, *args, **kwargs):
        return self.post(*args, **kwargs)


@method_decorator(login_required, name='dispatch')
class CollectionGroupDelete(DeleteView):
    model = CollectionGroup.collections.through

    def get_success_url(self):
        return (
            self.request.GET.get('return_url') or
            reverse('module:group-detail', kwargs={'group_slug': self.kwargs.get('group_slug')})
        )

    def get(self, request, *args, **kwargs):
        return self.post(request=request, *args, **kwargs)

    def get_queryset(self):
        return self.model.filter()

    def get_object(self, queryset=None):
        return self.model.objects.get(
            collection__owner=self.request.user,
            collection__slug=self.kwargs['slug'],
            collectiongroup__slug=self.kwargs['group_slug']
        )


@method_decorator(login_required, name='dispatch')
class ActivityCreate(BackURLMixin, CollectionSlugToContextMixin, ModalFormMixin, CreateView):
    model = Activity
    form_class = ActivityForm

    def get_initial(self):
        result = super().get_initial()
        if self.request.method == 'GET':
            result.update({
                'name': self.request.GET.get('name'),
                'source_name': self.request.GET.get('source_name'),
                'source_launch_url': self.request.GET.get('source_launch_url', '').replace(' ', '+'),
                'source_context_id': self.request.GET.get('source_context_id', '').replace(' ', '+'),
                'lti_consumer': self.request.GET.get('lti_consumer'),
                'stype': self.request.GET.get('stype'),
            })
        return result

    def form_valid(self, form):
        form.instance.collection = Collection.objects.get(slug=self.kwargs.get('collection_slug'))
        result = super().form_valid(form)
        return result


@method_decorator(login_required, name='dispatch')
class ActivityUpdate(CollectionSlugToContextMixin, ModalFormMixin, UpdateView):
    model = Activity
    form_class = ActivityForm
    context_object_name = 'activity'

    def get(self, request, *args, **kwargs):
        activity = self.get_object()
        if kwargs.get('direction'):
            try:
                # NOTE(wowkalucky): expects 'up', 'down' (also possible: 'top', 'bottom')
                getattr(activity, kwargs['direction'])()
            except AttributeError:
                log.exception("Unknown ordering method!")
            return redirect(reverse('module:collection-detail', kwargs={'slug': activity.collection.slug}))

        return super().get(request, *args, **kwargs)


@method_decorator(login_required, name='dispatch')
class ActivityDelete(DeleteView):
    model = Activity

    def get_success_url(self):
        return self.request.GET.get('return_url') or reverse(
            'module:collection-detail', kwargs={'slug': self.object.collection.slug}
        )

    def delete(self, request, *args, **kwargs):
        try:
            return super().delete(request, *args, **kwargs)
        except (ValidationError, TypeError):
            return redirect("{}?engine=failure".format(self.get_success_url()))


class SequenceItemDetail(LtiSessionMixin, DetailView):
    model = SequenceItem
    context_object_name = 'sequence_item'
    template_name = 'module/sequence_item.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
            policy = sequence.group.grading_policy.policy_instance(sequence=sequence)
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
    sequence_item_id, user_id, _activity, _suffix = outcome_request.lis_result_sourcedid.text.split(':')
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


def sync_collection(request, slug):
    """
    Synchronize collection immediately.
    """
    back_url = request.GET.get('back_url')
    collection = get_object_or_404(Collection, slug=slug)
    collection.save()
    log.debug("Immediate sync task is created, time: {}".format(collection.updated_at))
    tasks.sync_collection_engines.delay(
        collection_slug=slug, created_at=collection.updated_at
    )
    return redirect(reverse('module:collection-detail', kwargs={'slug': slug}) + '?back_url={}'.format(back_url))


def update_students_grades(request, group_slug):
    """
    Mandatory update students grade related to the collection-group.
    """
    back_url = request.GET.get('back_url')
    group = get_object_or_404(CollectionGroup, slug=group_slug)
    tasks.update_students_grades.delay(group_id=group.id)
    log.debug(f"Task with updating students grades related to the group {group.name} is started.")
    return redirect(reverse('module:group-detail', kwargs={'group_slug': group_slug}) + '?back_url={}'.format(back_url))


def preview_collection(request, slug):
    acitvities = [
        {
            'url': f'{reverse("lti:source-preview")}?source_id={a.id}&source_name={a.name}&source_lti_url='
                   f'{a.source_launch_url}&content_source_id={a.lti_consumer_id}',
            'pos': pos,
        }
        for pos, a in enumerate(get_list_or_404(Activity, collection__slug=slug), start=1)
    ]

    return render(
        request,
        template_name="module/sequence_preview.html",
        context={'activities': acitvities}
    )
