from django.conf.urls import url

from bridge_lti.consumer import source_preview
from bridge_lti.provider import lti_launch

urlpatterns = [
    url(r'^launch/?(?:/collection/(?P<collection_id>\d+)/group/(?P<group_slug>[\w-]+)'
        r'/unique_marker/(?P<unique_marker>[\w]+)/?)?$', lti_launch, name='launch'),
    url(r'^launch/?(?:/collection/(?P<collection_id>\d+)/group/(?P<group_slug>[\w-]+)/?)?$',
        lti_launch, name='launch'),
    url(r'^source/$', source_preview, name='source-preview'),
]
