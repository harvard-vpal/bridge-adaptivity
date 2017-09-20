import logging

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden
from django.shortcuts import redirect

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
            return HttpResponseForbidden("Cource content is available only through LTI protocol.")
        elif lti_session != cache.get(sequence_id):
            cache.set(sequence_id, lti_session)
            if request.session['Lti_strict_forward']:
                request.session['Lti_update_activity'] = True
                log.debug("Session is changed, activity update could be required: {}".format(
                    request.session['Lti_update_activity'])
                )
        return super(LtiSessionMixin, self).dispatch(request, *args, **kwargs)
