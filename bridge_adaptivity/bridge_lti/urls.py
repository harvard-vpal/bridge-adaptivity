from django.conf.urls import url

from bridge_lti.consumer import source_preview
from bridge_lti.provider import lti_launch

urlpatterns = ([
    url(r'^launch/?(?:/collection/(?P<collection_slug>[\w-]+)/group/(?P<group_slug>[\w-]+)/order/(?P<collection_order>\d+)/?)?(?:/unique_marker/(?P<unique_marker>[\w]+)/?)?$', lti_launch, name='launch'),
    url(r'^source/$', source_preview, name='source-preview'),
], 'lti')
