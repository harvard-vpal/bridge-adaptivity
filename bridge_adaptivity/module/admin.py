from django.contrib import admin

from .models import Sequence, SequenceItem, Collection, Activity, Log


class SequenceItemStackedInline(admin.StackedInline):
    model = SequenceItem


@admin.register(Sequence)
class SequenceAdmin(admin.ModelAdmin):
    inlines = [
        SequenceItemStackedInline,
    ]


class ActivityStackedInline(admin.StackedInline):
    model = Activity


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'owner_name', 'strict_forward']
    list_display_links = ['id', 'name']

    def owner_name(self, obj):
        return obj.owner.username

    owner_name.empty_value_display = '---'

    inlines = [
        ActivityStackedInline,
    ]


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    pass
