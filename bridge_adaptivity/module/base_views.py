# coding: utf-8
import logging

from module.mixins.views import BackURLMixin, OnlyMyObjectsMixin
from module.models import (
    Collection, CollectionGroup, Course
)

log = logging.getLogger(__name__)


class BaseCourseView(OnlyMyObjectsMixin, BackURLMixin):
    slug_url_kwarg = 'course_slug'
    slug_field = 'slug'
    model = Course


class BaseGroupView(OnlyMyObjectsMixin, BackURLMixin):
    slug_url_kwarg = 'group_slug'
    slug_field = 'slug'
    model = CollectionGroup


class BaseCollectionView(OnlyMyObjectsMixin, BackURLMixin):
    fields = ['name', 'metadata', 'strict_forward', 'owner']
    model = Collection
    ordering = ['id']
