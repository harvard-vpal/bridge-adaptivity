from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from ordered_model.admin import OrderedTabularInline

from .models import (
    Activity, Collection, CollectionGroup, CollectionOrder, Course, Engine, GradingPolicy, Log, Sequence, SequenceItem,
)


class SequenceItemStackedInline(admin.StackedInline):
    model = SequenceItem
    extra = 0


@admin.register(Sequence)
class SequenceAdmin(admin.ModelAdmin):
    inlines = (SequenceItemStackedInline,)


class ActivityStackedInline(OrderedTabularInline):
    model = Activity
    fields = [
        'order', 'move_up_down_links', 'name', 'atype', 'difficulty', 'points', 'source_launch_url',
        'source_name',
    ]
    readonly_fields = ('order', 'move_up_down_links',)
    extra = 0


@admin.register(CollectionOrder)
class CollectionOrderAdmin(admin.ModelAdmin):
    list_display = [field.name for field in CollectionOrder._meta.get_fields()]


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'owner_name', 'strict_forward']
    list_display_links = ['id', 'name']

    def owner_name(self, obj):
        return obj.owner.username

    owner_name.empty_value_display = '---'

    inlines = (ActivityStackedInline,)

    def get_urls(self):
        urls = super().get_urls()
        for inline in self.inlines:
            if hasattr(inline, 'get_urls'):
                urls = inline.get_urls(self) + urls
        return urls


class GroupForm(forms.ModelForm):
    class Meta:
        model = CollectionGroup
        fields = ('name', 'owner', 'description', 'collections', 'course', 'grading_policy', 'engine')
        widgets = {
            'collections': FilteredSelectMultiple(verbose_name='Collections', is_stacked=False)
        }


@admin.register(CollectionGroup)
class CollectionGroupAdmin(admin.ModelAdmin):
    form = GroupForm
    readonly_fields = ('slug',)
    list_display = ('name', 'slug', 'owner', 'grading_policy', 'engine')


@admin.register(Engine)
class EngineAdmin(admin.ModelAdmin):
    pass


@admin.register(GradingPolicy)
class GradingPolicyAdmin(admin.ModelAdmin):
    readonly_fields = ['name']
    list_display = ['name', 'collectiongroup', 'params']


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    pass


class GroupStackedInline(admin.StackedInline):
    model = CollectionGroup
    exclude = []
    readonly_fields = ('slug',)
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    inlines = (GroupStackedInline,)
    readonly_fields = ('slug',)
