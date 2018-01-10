import logging

from django import forms
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect
from models import Collection, Engine

log = logging.getLogger(__name__)


class CollectionIdToContextMixin(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(CollectionIdToContextMixin, self).get_context_data(**kwargs)
        context['current_collection_id'] = self.kwargs.get('collection_id')
        return context

    def form_valid(self, form):
        try:
            return super(CollectionIdToContextMixin, self).form_valid(form)
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
            if request.session['Lti_strict_forward']:
                request.session['Lti_update_activity'] = True
                log.debug("[StrictForward] Session is changed, activity update could be required: {}".format(
                    request.session['Lti_update_activity'])
                )
        return super(LtiSessionMixin, self).dispatch(request, *args, **kwargs)


class GroupEditFormMixin(object):
    def get_form(self):
        form = super(GroupEditFormMixin, self).get_form()
        collections = Collection.objects.filter(
            owner=self.request.user
        )
        form.fields['owner'].initial = self.request.user
        form.fields['engine'].initial = Engine.get_default_engine()
        form.fields['owner'].widget = forms.HiddenInput(attrs={'readonly': True})
        form.fields['collections'].queryset = collections
        return form


class CollectionMixin(object):
    def get_queryset(self):
        qs = Collection.objects.filter(owner=self.request.user)
        if 'group_slug' in self.kwargs:
            qs.filter(collection_groups__slug=self.kwargs['group_slug'])
        return qs
