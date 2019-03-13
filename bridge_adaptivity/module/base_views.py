"""
Base views: Course, Group(Module), Collection and CollectionOrder.
"""
# coding: utf-8
import logging

from module.mixins.views import BackURLMixin, OnlyMyObjectsMixin
from module.models import Collection, CollectionOrder, Course, ModuleGroup

log = logging.getLogger(__name__)


class BaseCourseView(OnlyMyObjectsMixin, BackURLMixin):
    """
    Base view for Course.
    """

    slug_url_kwarg = 'course_slug'
    slug_field = 'slug'
    model = Course


class BaseGetFormKwargs(OnlyMyObjectsMixin, BackURLMixin):
    """
    Call the parent get_form_kwargs method and then self get_form_kwargs variant.
    """

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        model_field_names = [f.name for f in self.model._meta.fields]
        filtered_get = {key: value for key, value in self.request.GET.items() if key in model_field_names}
        if filtered_get and not self.request.POST:
            kwargs['initial'] = filtered_get
        return kwargs


class BaseGroupView(BaseGetFormKwargs):
    """
    Base view for Group (Module).
    """

    slug_url_kwarg = 'group_slug'
    slug_field = 'slug'
    model = ModuleGroup


class BaseCollectionView(OnlyMyObjectsMixin, BackURLMixin):
    """
    Base view for Collection.
    """

    fields = ['name', 'slug', 'metadata', 'owner']
    model = Collection
    ordering = ['id']


class BaseCollectionOrderView(BaseGetFormKwargs):
    """
    Base view for CollectionOrder.
    """

    model = CollectionOrder
    ordering = ['group', 'order']
