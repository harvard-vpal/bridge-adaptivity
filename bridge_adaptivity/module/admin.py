from django.contrib import admin

from .models import Sequence, SequenceItem, Collection, Activity, Log


@admin.register(Sequence)
class SequenceAdmin(admin.ModelAdmin):
    pass


@admin.register(SequenceItem)
class SequenceItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'sequence', 'activity', 'position', 'score']


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'owner_name', 'strict_forward']
    list_display_links = ['id', 'name']

    def owner_name(self, obj):
        return obj.owner.username

    owner_name.empty_value_display = '---'


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    pass


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    pass
