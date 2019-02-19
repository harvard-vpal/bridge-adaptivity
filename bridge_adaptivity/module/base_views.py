"""
Base views: Course, Group(Module), Collection and CollectionOrder.
"""
# coding: utf-8
import logging

from module.mixins.views import BackURLMixin, OnlyMyObjectsMixin
from module.models import (
    Collection, CollectionGroup, Course, CollectionOrder
)

log = logging.getLogger(__name__)


class BaseCourseView(OnlyMyObjectsMixin, BackURLMixin):
    """
    Base view for Course.
    """
    slug_url_kwarg = 'course_slug'
    slug_field = 'slug'
    model = Course


class BaseGroupView(OnlyMyObjectsMixin, BackURLMixin):
    """
    Base view for Group (Module).
    """
    slug_url_kwarg = 'group_slug'
    slug_field = 'slug'
    model = CollectionGroup

    def get_form_kwargs(self):
        """
        Get form kwargs for CollectionGroup model.
        """
        kwargs = super().get_form_kwargs()
        model_field_names = [f.name for f in CollectionGroup._meta.fields]
        filtered_get = {key: value for key, value in self.request.GET.items() if key in model_field_names}
        if filtered_get and not self.request.POST:
            kwargs['initial'] = filtered_get
        return kwargs


class BaseCollectionView(OnlyMyObjectsMixin, BackURLMixin):
    """
    Base view for Collection.
    """
    fields = ['name', 'slug', 'metadata', 'strict_forward', 'owner']
    model = Collection
    ordering = ['id']


class BaseCollectionOrderView(OnlyMyObjectsMixin, BackURLMixin):
    """
    Base view for CollectionOrder
    """
    model = CollectionOrder
    ordering = ['group', 'order']

    def get_form_kwargs(self):
        """
        Get form kwargs for CollectionOrder model.
        """
        kwargs = super().get_form_kwargs()
        model_field_names = [f.name for f in CollectionOrder._meta.fields]
        filtered_get = {key: value for key, value in self.request.GET.items() if key in model_field_names}
        if filtered_get and not self.request.POST:
            kwargs['initial'] = filtered_get
        return kwargs
