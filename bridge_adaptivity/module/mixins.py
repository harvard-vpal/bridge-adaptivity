import logging

from django.core.cache import cache
from django.http import HttpResponseForbidden

log = logging.getLogger(__name__)


class CollectionIdToContextMixin(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(CollectionIdToContextMixin, self).get_context_data(**kwargs)
        context['current_collection_id'] = self.kwargs.get('collection_id')
        return context


class LtiSessionMixin(object):

    def dispatch(self, request, *args, **kwargs):
        lti_session = request.session.get('Lti_session')
        if not lti_session:
            log.error('Lti session is not found, Request cannot be processed')
            return HttpResponseForbidden("Cource content is available only through LTI protocol.")
        elif lti_session != cache.get('lti_session'):
            cache.set('lti_session', lti_session)
            request.session['Lti_update_activity'] = True
        return super(LtiSessionMixin, self).dispatch(request, *args, **kwargs)
