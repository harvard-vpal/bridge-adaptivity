from django.contrib import admin

from api.models import OAuthClient


@admin.register(OAuthClient)
class SequenceAdmin(admin.ModelAdmin):
    pass
