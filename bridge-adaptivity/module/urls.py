from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from .views import CollectionList, CollectionCreate, CollectionDetail, ActivityCreate, ActivityUpdate

urlpatterns = [
    url(r'^collection/$', login_required(CollectionList.as_view()), name='collection-list'),
    url(r'^collection/add/$', login_required(CollectionCreate.as_view()), name='collection-add'),
    url(r'^collection/(?P<pk>\d+)/$', login_required(CollectionDetail.as_view()), name='collection-detail'),
    url(r'^activity/(?P<collection_id>\d+)/add/$', login_required(ActivityCreate.as_view()), name='activity-add'),
    url(
        r'^activity/(?P<pk>\d+)/(?P<collection_id>\d+)/change/$',
        login_required(ActivityUpdate.as_view()),
        name='activity-change'
    ),
]
