import logging

from django import forms
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string

from module.forms import BaseCollectionForm, BaseGradingPolicyForm, CollectionGroupForm, GroupForm
from module.models import Collection, CollectionGroup, CollectionOrder, Course, Engine, GRADING_POLICY_NAME_TO_CLS

log = logging.getLogger(__name__)


class CollectionSlugToContextMixin(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_collection_slug'] = self.kwargs.get('collection_slug')
        return context

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except (ValidationError, TypeError):
            return redirect("{}?engine=failure".format(self.get_success_url()))


class LtiSessionMixin(object):

    def dispatch(self, request, *args, **kwargs):
        lti_session = request.session.get('Lti_session')
        sequence_id = request.session.get('Lti_sequence')
        if not lti_session:
            log.error('Lti session is not found, Request cannot be processed')
            raise PermissionDenied("Course content is available only through LTI protocol.")
        elif lti_session != cache.get(sequence_id):
            cache.set(sequence_id, lti_session)
            if request.session.get('Lti_strict_forward'):
                request.session['Lti_update_activity'] = True
                log.debug(
                    "[StrictForward] Session is changed, activity update could be required: {}".format(
                        request.session['Lti_update_activity']
                    )
                )
        return super().dispatch(request, *args, **kwargs)


class GroupEditFormMixin(object):
    form_class = GroupForm
    prefix = 'group'
    grading_prefix = 'grading'

    def get_form(self):
        form = super().get_form()
        form.fields['course'].queryset = Course.objects.filter(owner=self.request.user)
        return form


class CollectionOrderEditFormMixin(object):
    form_class = CollectionGroupForm
    prefix = 'collection_group'
    grading_prefix = 'grading'

    def get_grading_form_kwargs(self):
        """Return kwargs for GradingForm."""
        form_kw = dict(prefix=self.grading_prefix)
        if self.object and self.object.grading_policy:
            form_kw['instance'] = self.object.grading_policy
        return form_kw

    def form_valid(self, form):
        form_kw = self.get_grading_form_kwargs()
        policy = GRADING_POLICY_NAME_TO_CLS[self.request.POST.get('collection_group-grading_policy_name')]
        grading_policy_form = policy.get_form_class()
        grading_policy_form = grading_policy_form(self.request.POST, **form_kw)
        if grading_policy_form.is_valid():
            if 'params' not in grading_policy_form.cleaned_data:
                grading_policy_form.instance.params = {}
            grading_policy = grading_policy_form.save()
            form.cleaned_data['grading_policy'] = grading_policy
            response = super().form_valid(form)
        else:
            response = self.form_invalid(form)
            response.context_data["group"] = get_object_or_404(CollectionGroup, slug=self.kwargs.get('group'))
            if 'params' in grading_policy_form.cleaned_data:
                response.context_data['grading_policy_form'] = grading_policy_form
            return response
        return response

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        form_kw = self.get_grading_form_kwargs()
        post_or_none = self.request.POST if self.request.POST else None
        data['grading_policy_form'] = BaseGradingPolicyForm(post_or_none, **form_kw)
        return data

    def get_form(self):
        form = super().get_form()
        collections = Collection.objects.filter(
            owner=self.request.user
        )
        form.fields['engine'].initial = Engine.get_default()
        form.fields['collection'].queryset = collections
        if self.kwargs.get('collection_order_id') and self.kwargs.get('group'):
            collection_order = get_object_or_404(
                CollectionOrder,
                group__slug=self.kwargs['group'],
                id=self.kwargs['collection_order_id'],
            )
            if collection_order.grading_policy:
                form.initial['grading_policy_name'] = collection_order.grading_policy.name
        return form


class OnlyMyObjectsMixin(object):
    owner_field = 'owner'

    def get_queryset(self):
        qs = super().get_queryset()
        read_only_data = self.request.session.get('read_only_data')
        if read_only_data and getattr(self, 'filter', None) in read_only_data:
            return qs.filter(slug=read_only_data[self.filter])
        return qs.filter(**{self.owner_field: self.request.user})


class CollectionEditFormMixin(object):
    form_class = BaseCollectionForm
    prefix = 'collection'
    collection_prefix = 'collection'

    def get_collection_form_kwargs(self):
        """Return kwargs for GradingForm."""
        form_kw = dict(prefix=self.collection_prefix)
        if self.object and self.object.collection:
            form_kw['instance'] = self.object.collection
        return form_kw

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.POST.get('collection_group-collection'):
            form_kw = self.get_collection_form_kwargs()
            post_or_none = self.request.POST if self.request.POST else None
            context['collection_form'] = BaseCollectionForm(post_or_none, **form_kw)
        context["group"] = get_object_or_404(CollectionGroup, slug=self.kwargs.get('group'))
        return context

    def form_valid(self, form):
        form_kw = self.get_collection_form_kwargs()
        post_or_none = self.request.POST if self.request.POST else None
        collection_form = BaseCollectionForm(post_or_none, **form_kw)
        if self.request.POST.get('collection_group-collection'):
            response = super().form_valid(form)
        elif collection_form.is_valid():
            collection = collection_form.save()
            form.cleaned_data['collection'] = collection
            response = super().form_valid(form)
        else:
            response = self.form_invalid(form)
            response.context_data["group"] = get_object_or_404(CollectionGroup, slug=self.kwargs.get('group'))
        return response

    def get_form(self):
        form = super().get_form()
        form.fields['collection'].required = False
        return form


class BackURLMixin(object):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        back_url = self.request.GET.get('back_url')
        if back_url:
            context['back_url'] = back_url
        return context

    def get_success_url(self):
        return self.request.GET.get('return_url') or self.object.get_absolute_url()


class SetUserInFormMixin(object):
    owner_field_name = 'owner'

    def get_form(self):
        form = super().get_form()
        if form.fields.get(self.owner_field_name):
            form.fields['owner'].initial = self.request.user
            form.fields['owner'].widget = forms.HiddenInput(attrs={'readonly': True})
        return form


class ModalFormMixin(object):
    """
    Mixin for overwriting form validation response for modal form and specifying default modal form template suffix.
    """

    template_name_suffix = '_modal_form'

    def form_valid(self, form):
        """
        Return status code as Accepted and JSON {'status': 'ok} as submission result of the valid form.
        """
        super().form_valid(form)
        return JsonResponse(status=202, data={'status': 'ok'})


class LinkObjectsMixin(object):
    """
    This mixin add possibility to link objects using form.

    It will show popup message with form `self.link_form_class` and submit data to other view defined in
    `link_action_url` or propose to create new object by url `add_new_object_url`.
    """

    link_form_class = None
    link_object_name = 'collection'

    def get_link_form_kwargs(self):
        raise NotImplementedError("Method get_link_form_kwargs should be implemented in inherited classes.")

    def get_link_action_url(self):
        raise NotImplementedError("Link action URL not defined.")

    def get_has_available_objects(self, form):
        raise NotImplementedError("Method get_has_available_objects should be implemented in inherited classes.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.link_form_class(**self.get_link_form_kwargs())
        return_url = self.object.get_absolute_url()
        context.update({
            'link_objects_form': form,
            'has_available_objects': self.get_has_available_objects(form),
            'add_new_object_name': self.link_object_name,
            'link_action_url': self.get_link_action_url(),
            'add_new_object_url': (
                "{action_url}?back_url={return_url}&{object_name}={course.id}&return_url={return_url}"
            ).format(
                action_url=self.get_link_action_url(),
                return_url=return_url,
                course=self.object,
                object_name=self.context_object_name,
            )
        })
        return context


class JsonResponseMixin(object):
    def get_success_url(self):
        raise NotImplementedError("Inherited classes should implement get_success_url method.")

    def form_valid(self, form):
        form.save()
        return JsonResponse(dict(success=True, url=self.get_success_url()))

    def form_invalid(self, form):
        html = render_to_string(self.template_name, context={'form': form}, request=self.request)
        return JsonResponse(dict(success=False, html=html))
