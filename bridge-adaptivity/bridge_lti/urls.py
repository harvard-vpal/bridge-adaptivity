from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from .provider import lti_launch
from .views import LtiSourceList, LtiSourceDetail
from .consumer import content_source

urlpatterns = [
    url(r'^launch$', lti_launch, name='lti-provider-launch'),
    url(r'^sources/$', login_required(LtiSourceList.as_view()), name='source-list'),
    url(r'^sources/(?P<pk>\d+)/$', login_required(LtiSourceDetail.as_view()), name='source-detail'),
    url(r'^content_source(?P<pk>\d+)/$', content_source, name='content-source'),
]
