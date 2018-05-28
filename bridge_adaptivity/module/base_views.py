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

    def get_form_kwargs(self):
        kwargs = super(BaseGroupView, self).get_form_kwargs()
        model_field_names = [f.name for f in CollectionGroup._meta.fields]
        filtered_get = {key: value for key, value in list(self.request.GET.items()) if key in model_field_names}
        if filtered_get and not self.request.POST:
            kwargs['initial'] = filtered_get
        return kwargs


class BaseCollectionView(OnlyMyObjectsMixin, BackURLMixin):
    fields = ['name', 'metadata', 'strict_forward', 'owner']
    model = Collection
    ordering = ['id']
