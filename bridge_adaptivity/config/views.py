from logging import getLogger

from django.contrib.auth.views import LoginView
from django.http import HttpResponse

log = getLogger(__name__)


def health(request):
    return HttpResponse()


class BridgeLoginView(LoginView):
    """
    OverLoad Login Class view to make available read-only mode.
    """

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        if self.request.session.get('read_only_collection'):
            log.debug('Read-only view is active.')
            context['read_only_available'] = True
        return context
