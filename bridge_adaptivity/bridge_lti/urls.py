"""
LTI urls.
"""
from django.conf.urls import url

from bridge_lti.consumer import source_preview
from bridge_lti.provider import lti_launch

urlpatterns = ([
    url(
        (
            r'^launch(?:/collection_order/(?P<collection_order_slug>[\w-]+))?(?:/unique_marker/'
            r'(?P<unique_marker>[\w]+)/?)?$'
        ),
        lti_launch,
        name='launch'
    ),
    url(r'^source/$', source_preview, name='source-preview'),
], 'lti')
