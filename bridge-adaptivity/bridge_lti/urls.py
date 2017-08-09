from django.conf.urls import url

from bridge_lti.views import LtiSourceList, LtiSourceDetail
from . import views

urlpatterns = [
    url(r'^launch$', views.launch, name='launch'),
    url(r'^sources/$', LtiSourceList.as_view(), name='source-list'),
    url(r'^sources/(?P<pk>\d+)/$', LtiSourceDetail.as_view(), name='source-detail'),
]
