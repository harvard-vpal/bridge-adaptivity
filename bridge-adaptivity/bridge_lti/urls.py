from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from .provider import lti_launch
from .consumer import source_preview

urlpatterns = [
    url(r'^launch/(?P<collection_id>\d+)$', lti_launch, name='lti-provider-launch'),
    url(r'^source/$', login_required(source_preview), name='source-preview'),
]
