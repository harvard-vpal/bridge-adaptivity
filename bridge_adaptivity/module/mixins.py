import logging

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.conf import settings

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
            msg = """
                Your browser security settings require an additional step before starting the quiz.
                Please open https://courses.openedx.vpal.io/event and {}/lti/create_session in new
                browser tabs. Then close those tabs, and refresh this page. If you continue experiencing
                problems accessing the quiz, try decreasing your browser's security settings or using a
                different browser.
            """.format(settings.BRIDGE_HOST)
            return HttpResponseForbidden(msg)
        elif lti_session != cache.get(sequence_id):
            cache.set(sequence_id, lti_session)
            if request.session['Lti_strict_forward']:
                request.session['Lti_update_activity'] = True
                log.debug("[StrictForward] Session is changed, activity update could be required: {}".format(
                    request.session['Lti_update_activity'])
                )
        return super(LtiSessionMixin, self).dispatch(request, *args, **kwargs)
