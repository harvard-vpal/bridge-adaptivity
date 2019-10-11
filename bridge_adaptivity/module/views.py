from collections import defaultdict
import datetime
import logging
import urllib
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Q
from django.http import HttpResponse, HttpResponseNotFound
from django.http.response import Http404, JsonResponse
from django.shortcuts import get_list_or_404, get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.views.generic.edit import FormView
from lti import InvalidLTIConfigError, OutcomeRequest, OutcomeResponse
from lti.outcome_response import CODE_MAJOR_CODES, SEVERITY_CODES

from api.backends.api_client import get_active_content_sources, get_available_courses
from bridge_lti.models import LtiLmsPlatform, LtiUser
from common.utils import get_engine_and_collection_order, stub_page
from module import tasks, utils
from module.base_views import BaseCollectionOrderView, BaseCollectionView, BaseModuleGroupView
from module.consumers import CallbackSequenceConsumer
from module.forms import (
    ActivityForm, BaseCollectionForm, BaseGradingPolicyForm, CollectionOrderForm, ContributorPermissionForm,
    ModuleGroupForm
)
from module.mixins.views import (
    BackURLMixin, CollectionOrderEditFormMixin, CollectionSlugToContextMixin, GroupEditFormMixin,
    JsonResponseMixin, LinkObjectsMixin, LtiSessionMixin, ModalFormMixin, SetUserInFormMixin
)
from module.models import (
    Activity, Collection, CollectionOrder, ContributorPermission, GRADING_POLICY_NAME_TO_CLS, Log, ModuleGroup,
    Sequence, SequenceItem
)


log = logging.getLogger(__name__)

DEMO_USER = 'demo_lti_user'


@method_decorator(login_required, name='dispatch')
class ModuleGroupList(BaseModuleGroupView, ListView):
    context_object_name = 'groups'
    ordering = ['id']
    filter = 'group_slug'
    enable_sharing = True


@method_decorator(login_required, name='dispatch')
class GetCollectionForm(FormView):
    form_class = BaseCollectionForm
    template_name = 'module/collection_form.html'
    prefix = 'collection'

    def get_form_kwargs(self):
        form_kw = dict(prefix=self.prefix)
        return form_kw

    def get_form(self, form_class=None):
        form = super().get_form()
        form.fields['owner'].initial = self.request.user.id
        form.fields['name'].help_text = (
            "Name of the new Collection. You can choose available collections under the Collection settings block"
        )
        collection_id = self.request.GET.get('collection_id')
        if collection_id and Collection.objects.filter(id=collection_id).first():
            form.fields.clear()
        return form


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
        if self.kwargs.get('collection_order_slug'):

            collection_order_query = CollectionOrder.objects.filter(
                slug=self.kwargs.get('collection_order_slug'),
            )
            if self.request.GET.get('grading_policy'):
                collection_order_query = collection_order_query.filter(
                    grading_policy__name=self.request.GET.get('grading_policy')
                )
            collection_order = collection_order_query.first()
            if collection_order:
                kwargs['instance'] = collection_order.grading_policy
        return kwargs

    def get_form(self, form_class=None):
        self.form_class = self.get_form_class()
        form = super().get_form()
        gp = self.request.GET.get('grading_policy')
        if gp in GRADING_POLICY_NAME_TO_CLS:
            form.fields['name'].initial = self.request.GET.get('grading_policy')
        return form


@method_decorator(login_required, name='dispatch')
class ModuleGroupCreate(BaseModuleGroupView, SetUserInFormMixin, GroupEditFormMixin, ModalFormMixin, CreateView):
    pass


@method_decorator(login_required, name='dispatch')
class ModuleGroupDetail(CollectionOrderEditFormMixin, LinkObjectsMixin, BaseModuleGroupView, DetailView):
    context_object_name = 'group'
    link_form_class = CollectionOrderForm
    link_object_name = 'collection'
    filter = 'group_slug'
    enable_sharing = True

    def get_link_form_kwargs(self):
        return dict(user=self.request.user, group=self.object)

    def get_link_action_url(self):
        return reverse('module:collection-add')

    def get_has_available_objects(self, form):
        return form.fields['collection'].queryset.exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'bridge_host': settings.BRIDGE_HOST,
        })
        return context


class AddCollectionInGroup(CollectionOrderEditFormMixin, JsonResponseMixin, FormView):
    template_name = 'module/modals/course_add_group.html'
    form_class = CollectionOrderForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['group'] = get_object_or_404(ModuleGroup, slug=self.kwargs.get('group_slug'))
        return kwargs

    def get_success_url(self):
        return reverse('module:group-detail', kwargs=self.kwargs)


@method_decorator(login_required, name='dispatch')
class ModuleGroupUpdate(BaseModuleGroupView, SetUserInFormMixin, ModalFormMixin, UpdateView):
    form_class = ModuleGroupForm
    context_object_name = 'group'

    def get(self, request, *args, **kwargs):
        # ToDo(AndreyLykhoman): testing this order method
        if kwargs.get('order'):
            collection_order = CollectionOrder.objects.get(
                slug=kwargs.get('collection_order_slug')
            )
            try:
                getattr(collection_order, 'to')(int(kwargs['order']))
            except AttributeError:
                log.exception("Unknown ordering method!")
            return HttpResponse(status=201)
        return super().get(request, *args, **kwargs)


@method_decorator(login_required, name='dispatch')
class ModuleGroupShare(BaseModuleGroupView, SetUserInFormMixin, ModalFormMixin, UpdateView):
    template_name = 'module/modals/share_module_group.html'
    form_class = ContributorPermissionForm

    def get_success_url(self):
        return self.request.GET.get('return_url', reverse('module:group-detail', kwargs=self.kwargs))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model = context.get('object')
        if model:
            context['contributors'] = model.contributors.all()
        return context

    def form_valid(self, form):
        new_consumer_obj = form.cleaned_data.get('new_consumer_obj')
        if new_consumer_obj and form.instance.owner != new_consumer_obj:
            super().form_valid(form)
            form.fields['contributor_username'].help_text = "The new contributor added. You can add another one."
            form.fields['contributor_username'].initial = None
            return self.render_to_response(self.get_context_data(form=form, object=form.instance))
        else:
            self.form_invalid(form)


@method_decorator(login_required, name='dispatch')
class ContributorPermissionDelete(DeleteView):
    model = ContributorPermission

    def get_success_url(self):
        return self.request.GET.get(
            'return_url',
            reverse('module:group-detail', kwargs={"group_slug": self.kwargs.get("group_slug")})
        )

    def get_object(self):
        return self.model.objects.get(
            group__slug=self.kwargs.get("group_slug"), user__username=self.kwargs.get("username")
        )

    def get(self, *args, **kwargs):
        return self.post(*args, **kwargs)


@method_decorator(login_required, name='dispatch')
class ModuleGroupDelete(BaseModuleGroupView, DeleteView):
    def get_success_url(self):
        return self.request.GET.get('return_url') or reverse('module:group-list')

    def get(self, *args, **kwargs):
        return self.post(*args, **kwargs)


@method_decorator(login_required, name='dispatch')
class CollectionList(BaseCollectionView, ListView):
    context_object_name = 'collections'
    filter = 'collection_slug'
    # Note(AndreyLikhoman): Django.views.generic.ListView doesn't have default fields slug_url_kwarg and slug_field so
    #  these fields were added.
    slug_url_kwarg = 'slug'
    slug_field = 'slug'

    def get_context_data(self):
        # Note(AndreyLykhoman): This implementation must be a rewrite after changing ContributorPermission model. You
        #  should remove the 'owner' field because of the  'contributors' field contains the last one and additional
        #  contributors. Also, you should change the forms' and the views' logic of work that work with Module Group.
        context = super().get_context_data()
        # Get Module Groups where collections are used.
        mg = ModuleGroup.objects.filter(collections__in=list(context['object_list'])).distinct()
        # The "name" and "slug" are ModuleGroup's fields
        res = mg.values('name', 'slug', 'collections__slug').filter(
            Q(owner=self.request.user) | Q(contributors=self.request.user)
        )
        list_mg = list(res)
        result_dict = defaultdict(list)
        # make a dictionary like: "{..."collection_slug": [{"name": "Name", "slug": "Slug"},..], ...}"
        for mg_item in list_mg:
            result_dict[mg_item.get("collections__slug")].append(mg_item)
        context['avaliable_groups'] = dict(result_dict)
        return context


@method_decorator(login_required, name='dispatch')
class CollectionCreate(BaseCollectionView, SetUserInFormMixin, ModalFormMixin, CreateView):

    def form_valid(self, form):
        result = super().form_valid(form)
        if self.kwargs.get('group_slug'):
            group = ModuleGroup.objects.get(slug=self.kwargs['group_slug'])
            CollectionOrder.objects.create(group=group, collection=self.object)
        return result


@method_decorator(login_required, name='dispatch')
class CollectionUpdate(BaseCollectionView, SetUserInFormMixin, ModalFormMixin, UpdateView):

    def form_valid(self, form):
        """
        Return status code as Accepted and JSON {'status': 'ok', 'collection_slug': new_slug}.
        """
        super().form_valid(form)
        return JsonResponse(status=202, data={'status': 'ok', 'collection_slug': form.cleaned_data.get("slug")})


@method_decorator(login_required, name='dispatch')
class CollectionOrderUpdate(
    BaseCollectionOrderView,
    SetUserInFormMixin,
    CollectionOrderEditFormMixin,
    ModalFormMixin,
    UpdateView,
):

    def get_object(self):
        collection_order = CollectionOrder.objects.get(slug=self.kwargs.get("collection_order_slug"))
        self.collection_order_group_slug = collection_order.group.slug
        return collection_order

    def get_success_url(self):
        return reverse("module:group-detail", kwargs={'group_slug': self.collection_order_group_slug})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['group'] = self.object.group
        kwargs['read_only'] = self._set_read_only_collection()
        return kwargs

    def _set_read_only_collection(self):
        return bool(self.kwargs.get('collection_order_slug'))


class CollectionOrderAdd(
    BaseCollectionOrderView,
    SetUserInFormMixin,
    CollectionOrderEditFormMixin,
    ModalFormMixin,
    CreateView
):

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['group'] = get_object_or_404(ModuleGroup, slug=self.kwargs.get('group_slug'))
        kwargs['read_only'] = self._set_read_only_collection()
        return kwargs

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests: instantiate a blank version of the form.
        """
        result = super().get(request, *args, **kwargs)
        result.context_data["group"] = get_object_or_404(ModuleGroup, slug=self.kwargs.get('group_slug'))
        result.context_data['form'].fields['collection'].required = False
        result.context_data['form'].fields['collection'].empty_label = "--- Create a new Collection ---"
        result.context_data['collection_form'].fields['owner'].initial = self.request.user.id
        result.context_data['collection_form'].fields['name'].help_text = (
            "Name of the new Collection. You can choose available collections under the Collection settings block"
        )

        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST.get('collection_group-collection'):
            context['collection_form'] = None
        return context

    def get_success_url(self):
        return reverse("module:group-detail", kwargs={'group_slug': self.kwargs.get("group_slug")})

    def _set_read_only_collection(self):
        # NOTE(AndreyLykhoman): Return 'False' because we will able to choose a new collection to add.
        return False


@method_decorator(login_required, name='dispatch')
class CollectionDetail(BaseCollectionView, DetailView):
    context_object_name = 'collection'
    filter = 'collection_slug'

    def get(self, request, *args, **kwargs):
        try:
            self.get_object()
        except Http404:
            collection_slug = request.GET.get('collection_slug')
            if collection_slug:
                return redirect(reverse("module:collection-detail", kwargs={'slug': collection_slug}))
            return redirect(reverse('module:collection-list'))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        selected_content_sources = list(map(int, self.request.GET.getlist('content_source', [])))
        activities = Activity.objects.filter(collection=self.object).select_related('lti_content_source')
        context = super().get_context_data(**kwargs)
        context['render_fields'] = ['name', 'tags', 'difficulty', 'points', 'source']
        context['activities'] = activities
        context['not_active_content_source'] = activities.filter(lti_content_source__is_active=False).order_by(
            "lti_content_source"
        ).distinct("lti_content_source").values_list('lti_content_source__name', flat=True)
        context['content_sources'] = self.get_content_source_list(selected_content_sources)
        context['source_courses'], context['errors_content_source'] = get_available_courses(
            self.request, selected_content_sources
        )
        context['activity_form'] = ActivityForm(initial={'collection': self.object})
        context['sync_available'] = self.object.collection_groups.exists()
        engine_failure = self.request.GET.get('engine')
        if engine_failure:
            context['engine'] = engine_failure
        return context

    def get_content_source_list(self, selected_content_sources):
        return [
            {
                'name': source.name,
                'id': source.id,
                'checked': 'checked' if not selected_content_sources or source.id in selected_content_sources else ''
            }
            for source in get_active_content_sources(request=self.request, not_allow_empty_source_id=False)
        ]


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
    model = CollectionOrder

    def get_success_url(self):
        return (
            self.request.GET.get('return_url') or
            reverse('module:group-detail', kwargs={'group_slug': self.object.group.slug})
        )

    def get(self, request, *args, **kwargs):
        return self.post(request=request, *args, **kwargs)

    def get_queryset(self):
        return self.model.filter()

    def get_object(self, queryset=None):
        return self.model.objects.get(slug=self.kwargs['collection_order_slug'])


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
                'lti_content_source': self.request.GET.get('lti_content_source'),
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
        """
        To Update activity by a GET request.

        Updating activities order and running update method in the superclass. The drag and drop feature uses this view.
        """
        activity = self.get_object()
        # NOTE(AndreyLykhoman): Changing activity's order if kwargs contains the 'order' param.
        if kwargs.get('order'):
            try:
                getattr(activity, 'to')(int(kwargs['order']))
            except AttributeError:
                log.exception("Unknown ordering method!")
            return HttpResponse(status=201)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        To Update activity by a POST request.

        Updating activity and changing the activity's order if activity changes the type.
        """
        activity = self.get_object()
        if request.POST.get("atype") != activity.atype:
            # NOTE(AndreyLykhoman): Excluding activity from atype group and reorder other activities. The autocommit
            #  was disabled in this part of code in order to send one query to DB.
            ordering_queryset = activity.get_ordering_queryset().exclude(pk=activity.pk)
            if ordering_queryset.exists():
                transaction.set_autocommit(False)
                try:
                    for index, element in enumerate(ordering_queryset):
                        element.order = index
                        element.save()
                except Exception:
                    transaction.rollback()
                    raise
                else:
                    transaction.commit()
                finally:
                    transaction.set_autocommit(True)
            # NOTE(AndreyLykhoman): Calculate a new activity's order
            new_order = 0
            tmp_activity = Activity.objects.filter(
                collection=activity.collection,
                atype=request.POST.get("atype")
            ).first()
            if tmp_activity:
                new_order = 1 + tmp_activity.get_ordering_queryset().latest('order').order

            activity.atype, activity.order = request.POST.get("atype"), new_order
            activity.save()
        result = super().post(request, *args, **kwargs)
        return result


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
        context['forbidden'] = True
        if not self.request.GET.get('forbidden'):
            context['forbidden'], _, _ = _check_next_forbidden(self.object.pk)
        sequence_items = SequenceItem.objects.filter(sequence=self.object.sequence)
        last_item = sequence_items.last()
        if (
            self.request.session.get('Lti_update_activity') and
            len(sequence_items) > 1 and
            last_item.is_problem and
            not last_item.score
        ):
            sequence_items = sequence_items[:len(sequence_items) - 1]
        context['sequence_items'] = sequence_items
        log.debug("Sequence Items on the page: {}".format(len(sequence_items)))

        Log.objects.create(
            sequence_item=self.object,
            log_type=Log.OPENED
        )
        return context


@method_decorator(login_required, name='dispatch')
class SequenceDelete(DeleteView):
    model = Sequence

    def get_success_url(self):
        return self.request.GET.get('return_url') or reverse(
            'module:group-detail', kwargs={'group_slug': self.object.group.slug}
        )

    def delete(self, request, *args, **kwargs):
        # NOTE(idegtiarov) ensure that sequence corresponds to the demo_user before deleting
        # if self.get_object().lti_user.user_id == DEMO_USER:
        if Sequence.objects.filter(id=self.kwargs.get('pk'), lti_user__user_id=DEMO_USER).exists():
            cache.delete(settings.TEST_SEQUENCE_SUFFIX)
            return super().delete(request, *args, **kwargs)
        else:
            return redirect(self.get_success_url())

    def get(self, request, *args, **kwargs):
        return self.post(request=request, *args, **kwargs)


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
        sequence_item.sequence.collection_order.strict_forward and
        sequence_item.score is None
    )
    log.debug(f"Next item forbidden: {next_forbidden}, last_item: {last_item}, sequence_item_id: {sequence_item.id}")
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
        return redirect("{}?forbidden=true".format(
            reverse('module:sequence-item', kwargs={'pk': sequence_item.id}))
        )

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
            policy = sequence.collection_order.grading_policy.policy_instance(
                sequence=sequence
            )
            policy.send_grade()
            if not activity:
                if sequence.completed:
                    return redirect(reverse('module:sequence-complete', kwargs={'pk': sequence_item.sequence_id}))
                return stub_page(
                    request,
                    title="Warning",
                    message="Cannot get next activity from the engine.",
                    tip="Try again later or connect with the instructor."
                )

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
    return redirect(
        reverse('module:sequence-item', kwargs={'pk': next_sequence_item.id})
    )


class SequenceComplete(LtiSessionMixin, DetailView):
    model = Sequence
    template_name = 'module/sequence_complete.html'


def _check_and_build_web_socket_message(sequence):
    """
    Build a dictionary with data for callback by Web Socket.

    Check flags ui_option, congratulation_message and validate score.
    """
    web_socket_message_dict = {"is_button_enable": True}
    grade = sequence.collection_order.grading_policy.calculate_grade(sequence)
    if sequence.collection_order.congratulation_message and grade >= settings.CONGRATULATION_SCORE_LEVEL:
        web_socket_message_dict["is_show_pop_up"] = True

    if sequence.collection_order.ui_option:
        web_socket_message_dict["ui_details"] = sequence.sequence_ui_details()

    return web_socket_message_dict


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
    web_socket_message_dict = _check_and_build_web_socket_message(sequence)
    CallbackSequenceConsumer.send_message_to_channel(
        f'{sequence_item.id}_{sequence_item.position}', web_socket_message_dict
    )
    if sequence.lis_result_sourcedid:
        policy = sequence.collection_order.grading_policy.policy_instance(
            sequence=sequence, request=request, user_id=user_id
        )
        policy.send_grade()

    return HttpResponse(xml, content_type="application/xml")


def sync_collection(request, slug, api_request=None):
    """
    Synchronize collection immediately.
    """
    back_url = request.GET.get('back_url')
    collection = get_object_or_404(Collection, slug=slug)
    collection.save()
    log.debug("Immediate sync task is created, time: {}".format(collection.updated_at))
    task = tasks.sync_collection_engines.delay(
        collection_slug=slug, created_at=collection.updated_at
    )
    if api_request:
        return task.collect(timeout=settings.CELERY_RESULT_TIMEOUT)
    return redirect(
        reverse('module:collection-detail', kwargs={'slug': collection.slug}) + '?back_url={}'.format(back_url)
    )


def update_students_grades(request, collection_order_slug):
    """
    Mandatory update students grade related to the collection-group.
    """
    back_url = request.GET.get('back_url')
    colection_order = get_object_or_404(CollectionOrder, slug=collection_order_slug)
    tasks.update_students_grades.delay(collection_order_slug=collection_order_slug)
    log.debug(
        f"Task with updating students grades related to the colection_order with id {colection_order.id} is started."
    )
    return redirect(reverse(
        'module:group-detail', kwargs={'group_slug': colection_order.group.slug}
    ) + '?back_url={}'.format(back_url))


def preview_collection(request, slug):
    acitvities = [
        {
            'url': (
                f'{reverse("lti:source-preview")}?source_id={a.id}&source_name={urllib.parse.quote_plus(a.name)}'
                f'&source_lti_url={a.source_launch_url}&content_source_id={a.lti_content_source_id}'
            ),
            'pos': pos,
        }
        for pos, a in enumerate(get_list_or_404(Activity, collection__slug=slug), start=1)
    ]
    return render(
        request,
        template_name="module/sequence_preview.html",
        context={
            'activities': acitvities,
            'back_url': (
                f"{reverse('module:collection-detail', kwargs={'slug': slug})}"
                f"?back_url={request.GET.get('back_url')}"
            )
        }
    )


def demo_collection(request, collection_order_slug):
    """
    View for the demonstration and testing of the adaptivity behaviour.
    """
    __, collection_order = get_engine_and_collection_order(collection_order_slug)

    lti_lms_platform = LtiLmsPlatform.objects.first()
    test_lti_user, created = LtiUser.objects.get_or_create(
        user_id=DEMO_USER,
        lti_lms_platform=lti_lms_platform,
    )

    test_sequence, created = Sequence.objects.get_or_create(
        lti_user=test_lti_user,
        collection_order=collection_order
    )

    strict_forward = collection_order.strict_forward
    request.session['Lti_sequence'] = test_sequence.id
    request.session['Lti_strict_forward'] = strict_forward

    back_url = request.GET.get('back_url', '')

    context = {
        'sequence_pk': test_sequence.id,
        'back_url': back_url,
        'forbidden': request.GET.get('forbidden', ''),
    }

    if created or not test_sequence.items.exists():
        suffix = int(datetime.datetime.now().timestamp())
        cache.set(settings.TEST_SEQUENCE_SUFFIX, suffix)
        test_sequence.suffix = suffix
        test_sequence.save()
        log.debug("Sequence {} was created".format(test_sequence))
        start_activity = utils.choose_activity(sequence=test_sequence)
        if not start_activity:
            log.warning('Instructor configured empty Collection.')
            return stub_page(
                request,
                title="Warning",
                message="Cannot get the first question to start.",
                tip="Please try again later",
                demo=True,
                sequence=test_sequence,
                back_url=back_url,
            )
        sequence_item = SequenceItem.objects.create(
            sequence=test_sequence,
            activity=start_activity,
            position=1
        )
        next_forbidden, _, _ = _check_next_forbidden(sequence_item.id)
        context.update({"forbidden": next_forbidden})
    else:
        s_item_id = request.GET.get('sequence_item_id') or test_sequence.items.last().id
        log.debug(f'SequienceItem id: {s_item_id}')
        next_forbidden, last_item, sequence_item = _check_next_forbidden(s_item_id)
        position = int(request.GET.get('position') or 1)
        if not (next_forbidden and position > sequence_item.position):
            update_activity = request.session.pop('Lti_update_activity', None)
            sequence_item, sequence_complete, stub = utils.select_next_sequence_item(
                sequence_item, update_activity, last_item, position,
            )
            next_forbidden, _, _ = _check_next_forbidden(sequence_item.id)
            context.update({"forbidden": next_forbidden})

            if sequence_complete:
                context.update(
                    {'sequence_items': test_sequence.items.all(), 'demo': True, 'sequence_item': sequence_item}
                )
                return render(
                    request,
                    template_name='module/sequence_complete.html',
                    context=context)
            elif stub:
                return stub_page(
                    request,
                    title="Warning",
                    message="Cannot get next activity from the engine.",
                    tip="Try again later or connect with the instructor.",
                    demo=True,
                    sequence=test_sequence,
                    back_url=back_url,
                )

    context.update({
        'sequence_item': sequence_item,
        'sequence_items': test_sequence.items.all(),
        'demo': True,
        'position': sequence_item.position + 1
    })
    return render(
        request,
        template_name="module/sequence_item.html",
        context=context
    )
