import logging

from django.views.generic import DetailView, ListView

from bridge_lti.models import LtiSource

logger = logging.getLogger(__name__)


class LtiSourceList(ListView):
    model = LtiSource
    context_object_name = 'lti_sources'
    paginate_by = 10


class LtiSourceDetail(DetailView):
    model = LtiSource
    context_object_name = 'lti_source'
