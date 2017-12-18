from django.contrib import admin
from ordered_model.admin import OrderedTabularInline

from .models import Activity, Collection, Log, Sequence, SequenceItem
from models import CollectionGroup, Engine


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
        'source_name', 'source_context_id'
    ]
    readonly_fields = ('order', 'move_up_down_links',)
    extra = 0


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'threshold', 'owner_name', 'strict_forward']
    list_display_links = ['id', 'name']

    def owner_name(self, obj):
        return obj.owner.username

    owner_name.empty_value_display = '---'

    inlines = (ActivityStackedInline,)

    def get_urls(self):
        urls = super(CollectionAdmin, self).get_urls()
        for inline in self.inlines:
            if hasattr(inline, 'get_urls'):
                urls = inline.get_urls(self) + urls
        return urls


@admin.register(CollectionGroup)
class CollectionGroupAdmin(admin.ModelAdmin):
    model = CollectionGroup


@admin.register(Engine)
class EngineAdmin(admin.ModelAdmin):
    pass

@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    pass
