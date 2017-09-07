from django.conf.urls import url
from django.urls import reverse_lazy
from django.views.generic import RedirectView

from module.views import (
    CollectionList, CollectionCreate, CollectionDetail, ActivityCreate, ActivityUpdate, ActivityDelete,
    SequenceItemDetail, sequence_item_next, SequenceComplete, callback_sequence_item_grade)

urlpatterns = [
    url(r'^collection/$', CollectionList.as_view(), name='collection-list'),
    url(r'^collection/add/$', CollectionCreate.as_view(), name='collection-add'),
    url(r'^collection/(?P<pk>\d+)/$', CollectionDetail.as_view(), name='collection-detail'),
    url(r'^activity/(?P<collection_id>\d+)/add/$', ActivityCreate.as_view(), name='activity-add'),
    url(
        r'^activity/(?P<pk>\d+)/(?P<collection_id>\d+)/change/$',
        ActivityUpdate.as_view(),
        name='activity-change'
    ),
    url(
        r'^activity/(?P<pk>\d+)/delete/$',
        ActivityDelete.as_view(),
        name='activity-delete'
    ),
    url(r'^sequence_item/(?P<pk>\d+)/$', SequenceItemDetail.as_view(), name='sequence-item'),
    url(r'^sequence_item/(?P<pk>\d+)/next/$', sequence_item_next, name='sequence-item-next'),
    url(r'^sequence_complete/(?P<pk>\d+)/$', SequenceComplete.as_view(), name='sequence-complete'),
    url(r'^$', RedirectView.as_view(url=reverse_lazy('module:collection-list'))),

    # Source outcome service endpoint
    url(r'^callback_grade/$', callback_sequence_item_grade, name='sequence-item-grade')
]
