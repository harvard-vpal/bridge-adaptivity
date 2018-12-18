from django.contrib.auth.views import LoginView
from django.http import HttpResponse
from logging import getLogger

log = getLogger(__name__)


def health(request):
    return HttpResponse()


class BridgeLoginView(LoginView):

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        log.error(f'Do we have a session: {self.request.session.values()}')
        if self.request.session.get('read_only_collection'):
            context['read_only_available'] = True
        return context
