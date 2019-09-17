from django.conf.urls import url
from django.urls import path, re_path, reverse_lazy
from django.views.generic import RedirectView

from module.views import (
    ActivityCreate, ActivityDelete, ActivityUpdate, AddCollectionInGroup, callback_sequence_item_grade,
    CollectionCreate, CollectionDelete, CollectionDetail, CollectionGroupDelete, CollectionList, CollectionOrderAdd,
    CollectionOrderUpdate, CollectionUpdate, ContributorPermissionDelete, demo_collection, GetCollectionForm,
    GetGradingPolicyForm, ModuleGroupCreate, ModuleGroupDelete, ModuleGroupDetail, ModuleGroupList, ModuleGroupShare,
    ModuleGroupUpdate, preview_collection, sequence_item_next, SequenceComplete, SequenceDelete, SequenceItemDetail,
    sync_collection, update_students_grades
)

urlpatterns = ([
    url(r'^group/$', ModuleGroupList.as_view(), name='group-list'),
    re_path(r'^(?:course/(?P<course_slug>[\w-]+)/)?group/add/?$', ModuleGroupCreate.as_view(), name='group-add'),
    url(r'^group/(?P<group_slug>[\w-]+)/$', ModuleGroupDetail.as_view(), name='group-detail'),
    url(r'^group/(?P<group_slug>[\w-]+)/change/?$', ModuleGroupUpdate.as_view(), name='group-change'),
    url(r'^group/(?P<group_slug>[\w-]+)/delete/?$', ModuleGroupDelete.as_view(), name='group-delete'),
    path("group/<slug:group_slug>/share/add/", ModuleGroupShare.as_view(), name="group-share"),
    path(
        "group/<slug:group_slug>/share/remove/<username>/",
        ContributorPermissionDelete.as_view(),
        name="group-share-remove"
    ),
    url(r'^group/(?P<group_slug>[\w-]+)/add_collection/?$', AddCollectionInGroup.as_view(),
        name='add-collection-to-group'),
    url(r'^collection_order/(?P<collection_order_slug>[\w-]+)/delete/', CollectionGroupDelete.as_view(),
        name='collection-group-delete'),
    url(
        r'collection_order/(?:(?P<collection_order_slug>[\w-]+)/)?grading_policy_form/?$',
        GetGradingPolicyForm.as_view(),
        name='grading_policy_form'
    ),
    url(r'collection/collection_form/$', GetCollectionForm.as_view(), name='collection_form'),
    url(r'^(?:group/(?P<group_slug>[\w-]+)/)?collection/$', CollectionList.as_view(), name='collection-list'),
    url(r'^(?:group/(?P<group_slug>[\w-]+)/)?collection/add/$', CollectionCreate.as_view(), name='collection-add'),
    path('collection/<slug:slug>/change/', CollectionUpdate.as_view(), name='collection-change'),
    url(
        r'collection_order/(?P<collection_order_slug>[\w-]+)/change$',
        CollectionOrderUpdate.as_view(),
        name='collection-order-change'
    ),
    url(
        r'group/(?P<group_slug>[\w-]+)/add/collection_order/$',
        CollectionOrderAdd.as_view(),
        name='collection-order-add'
    ),
    url(
        r'^(?:group/(?P<group_slug>[\w-]+)/)?collection/(?P<slug>[\w-]+)/$',
        CollectionDetail.as_view(),
        name='collection-detail'
    ),
    url(
        r'^(?:group/(?P<group_slug>[\w-]+)/)?collection/(?P<slug>[\w-]+)/delete/?$',
        CollectionDelete.as_view(),
        name='collection-delete'
    ),
    url(
        r'collection_order/(?P<collection_order_slug>[\w-]+)/demo',
        demo_collection,
        name="demo"
    ),
    path('sequence/<int:pk>', SequenceDelete.as_view(), name="delete_sequence"),
    url(
        r'^collection_order/(?P<collection_order_slug>[\w-]+)/move/(?P<order>\d+)?$',
        ModuleGroupUpdate.as_view(),
        name='collection-move'
    ),
    url(r'^activity/(?P<collection_slug>[\w-]+)/add/$', ActivityCreate.as_view(), name='activity-add'),
    url(
        r'^activity/(?P<pk>\d+)/(?P<collection_slug>[\w-]+)/change/$',
        ActivityUpdate.as_view(),
        name='activity-change'
    ),
    url(
        r'^activity/(?P<pk>\d+)/move/(?P<order>\d+)?$',
        ActivityUpdate.as_view(),
        name='activity-move'
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
    url(r'^callback_grade/$', callback_sequence_item_grade, name='sequence-item-grade'),

    # Sync collection with relative engines
    url(r'^collection/(?P<slug>[\w-]+)/sync/$', sync_collection, name='collection-sync'),

    # Manually update students grades related to the collection-group
    url(
        r'collection_order/(?P<collection_order_slug>[\w-]+)/update_grades/',
        update_students_grades,
        name='update_grades'
    ),

    path('collection/<slug:slug>/preview/', preview_collection, name='collection-preview'),
], 'module')
