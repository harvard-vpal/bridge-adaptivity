from django.conf.urls import url
from django.urls import path, re_path, reverse_lazy
from django.views.generic import RedirectView

from module.views import (
    ActivityCreate, ActivityDelete, ActivityUpdate, AddCollectionInGroup, callback_sequence_item_grade,
    CollectionCreate, CollectionDelete, CollectionDetail, CollectionGroupDelete, CollectionList, CollectionUpdate,
    CourseAddGroup, CourseCreate, CourseDelete, CourseDetail, CourseList, CourseRmGroup, CourseUpdate,
    GetGradingPolicyForm, GroupCreate, GroupDelete, GroupDetail, GroupList, GroupUpdate, preview_collection,
    sequence_item_next, SequenceComplete, SequenceItemDetail, sync_collection, update_students_grades)

urlpatterns = ([
    url(r'^course/$', CourseList.as_view(), name='course-list'),
    url(r'^course/add/?$', CourseCreate.as_view(), name='course-add'),
    url(r'^course/(?P<course_slug>[\w-]+)/$', CourseDetail.as_view(), name='course-detail'),
    url(r'^course/(?P<course_slug>[\w-]+)/change/?$', CourseUpdate.as_view(), name='course-change'),
    url(r'^course/(?P<course_slug>[\w-]+)/delete/?$', CourseDelete.as_view(), name='course-delete'),
    url(r'^course/(?P<course_slug>[\w-]+)/add_group/?$', CourseAddGroup.as_view(), name='add-group-to-course'),
    url(r'^course/(?P<course_slug>[\w-]+)/rm_group/(?P<group_slug>[\w-]+)?/?$', CourseRmGroup.as_view(),
        name='rm-group-from-course'),

    url(r'^group/$', GroupList.as_view(), name='group-list'),
    re_path(r'^(?:course/(?P<course_slug>[\w-]+)/)?group/add/?$', GroupCreate.as_view(), name='group-add'),
    url(r'^group/(?P<group_slug>[\w-]+)/$', GroupDetail.as_view(), name='group-detail'),
    url(r'^group/(?P<group_slug>[\w-]+)/change/?$', GroupUpdate.as_view(), name='group-change'),
    url(r'^group/(?P<group_slug>[\w-]+)/delete/?$', GroupDelete.as_view(), name='group-delete'),
    url(r'^group/(?P<group_slug>[\w-]+)/add_collection/?$', AddCollectionInGroup.as_view(),
        name='add-collection-to-group'),

    url(r'^group/(?P<group_slug>[\w-]+)/delete/(?P<slug>[\w-]+)?$', CollectionGroupDelete.as_view(),
        name='collection-group-delete'),

    url(r'group(?:/(?P<group_slug>[\w-]*))?/grading_policy_form/?$', GetGradingPolicyForm.as_view(),
        name='grading_policy_form'),

    url(r'^(?:group/(?P<group_slug>[\w-]+)/)?collection/$', CollectionList.as_view(), name='collection-list'),
    url(r'^(?:group/(?P<group_slug>[\w-]+)/)?collection/add/$', CollectionCreate.as_view(),
        name='collection-add'),
    path('collection/<slug:slug>/change/', CollectionUpdate.as_view(), name='collection-change'),
    url(r'^(?:group/(?P<group_slug>[\w-]+)/)?collection/(?P<slug>[\w-]+)/$', CollectionDetail.as_view(),
        name='collection-detail'),
    url(r'^(?:group/(?P<group_slug>[\w-]+)/)?collection/(?P<slug>[\w-]+)/delete/?$', CollectionDelete.as_view(),
        name='collection-delete'),

    url(r'^activity/(?P<collection_slug>[\w-]+)/add/$', ActivityCreate.as_view(), name='activity-add'),
    url(
        r'^activity/(?P<pk>\d+)/(?P<collection_slug>[\w-]+)/change/$',
        ActivityUpdate.as_view(),
        name='activity-change'
    ),
    url(
        r'^activity/(?P<pk>\d+)/move/(?P<direction>(up|down))/$',
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
    path('group/<slug:group_slug>/update_grades/', update_students_grades, name='update_grades'),

    path('collection/<slug:slug>/preview/', preview_collection, name='collection-preview'),
], 'module')
