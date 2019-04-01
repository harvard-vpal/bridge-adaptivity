from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from ordered_model.admin import OrderedTabularInline

from .models import (
    Activity, Collection, CollectionOrder, ContributorPermission, Engine, GradingPolicy, Log, ModuleGroup, Sequence,
    SequenceItem
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
        'order', 'move_up_down_links', 'name', 'atype', 'difficulty', 'points', 'source_launch_url', 'source_name',
    ]
    readonly_fields = ('order', 'move_up_down_links',)
    extra = 0


@admin.register(CollectionOrder)
class CollectionOrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'order', 'group', 'collection', 'grading_policy', 'engine', 'strict_forward', 'ui_option', 'ui_next',
    ]


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'owner_name']
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


class ModuleGroupForm(forms.ModelForm):
    class Meta:
        model = ModuleGroup
        fields = (
            'name', 'owner', 'description', 'collections'
        )
        widgets = {
            'collections': FilteredSelectMultiple(verbose_name='Collections', is_stacked=False)
        }


@admin.register(ModuleGroup)
class ModuleGroupAdmin(admin.ModelAdmin):
    form = ModuleGroupForm
    list_display = ('name', 'owner')


@admin.register(Engine)
class EngineAdmin(admin.ModelAdmin):
    pass


@admin.register(GradingPolicy)
class GradingPolicyAdmin(admin.ModelAdmin):
    readonly_fields = ['name']
    list_display = ['name', 'collectionorder', 'params']


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    readonly_fields = (
        'sequence_item',  # populating dropdown may not be feasible for large number of available sequence items
    )
    # reduces number of db queries
    list_select_related = (
        'sequence_item',
        'sequence_item__activity',
        'sequence_item__sequence',
        'sequence_item__sequence__lti_user',
    )


class ModuleGroupStackedInline(admin.StackedInline):
    model = ModuleGroup
    extra = 0


@admin.register(ContributorPermission)
class ContributorPermissionAdmin(admin.ModelAdmin):
    pass
