from django.conf.urls import url

from .provider import lti_launch
from .consumer import source_preview

urlpatterns = [
    url(r'^launch/(?P<collection_id>\d*)$', lti_launch, name='launch'),
    url(r'^source/$', source_preview, name='source-preview'),
]
