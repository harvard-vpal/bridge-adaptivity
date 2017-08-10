from .models import *
from django.contrib import admin


@admin.register(Sequence)
class SequenceAdmin(admin.ModelAdmin):
    pass


@admin.register(SequenceItem)
class SequenceItemAdmin(admin.ModelAdmin):
    pass


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    pass

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    pass


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    pass
