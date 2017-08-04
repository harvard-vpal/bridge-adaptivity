from django.contrib import admin

# Register your models here.
from .models import *
from bridge_lti.models import *

def get_generic_label(obj):
	return "{}: {}".format(obj._meta.model_name, obj.pk)

class ActivityAdmin(admin.ModelAdmin):
	list_display = ['name','id', 'type','module']
	list_filter = ['type']

class SequenceItemAdmin(admin.ModelAdmin):
	list_display = ['get_label','activity','get_module','position','method','get_username', 'get_user',]
	list_filter = ['user_module']

	def get_user(self, obj):
		return obj.user_module.user.pk
	get_user.short_description = 'user'
	get_user.admin_order_field = 'user_module__user'

	def get_username(self, obj):
		return obj.user_module.user.username
	get_username.short_description = 'username'
	get_username.admin_order_field = 'user_module__user'

	def get_module(self, obj):
		return obj.user_module.module.pk
	get_module.short_description = 'module'
	get_module.admin_order_field = 'user_module__module'

	def get_label(self,obj):
		return get_generic_label(obj)

class LtiParametersAdmin(admin.ModelAdmin):
	list_display = ['get_label','user_module', 'get_module', 'get_user', 'lis_person_sourcedid', 'timestamp_last_launch']
	readonly_fields = ['timestamp_last_launch']

	def get_module(self, obj):
		return obj.user_module.module.pk
	get_module.short_description = 'module'
	get_module.admin_order_field = 'user_module__module'

	def get_user(self, obj):
		return obj.user_module.user.pk
	get_user.short_description = 'user'
	get_user.admin_order_field = 'user_module__user'

	def get_label(self,obj):
		return get_generic_label(obj)

class AttemptAdmin(admin.ModelAdmin):
	list_display = ['get_label','activity', 'points','max_points','sequence_item','user','timestamp']
	readonly_fields = ['timestamp']
	list_filter = ['user','activity']
	def get_label(self,obj):
		return get_generic_label(obj)

class UserModuleAdmin(admin.ModelAdmin):
	list_display = ['get_label','user','module','grade','last_position']
	list_filter = ['user','module']
	def get_label(self,obj):
		return get_generic_label(obj)

admin.site.register(Module)
admin.site.register(Activity, ActivityAdmin)
# admin.site.register(Problem)
# admin.site.register(Answer)
# admin.site.register(Event)
admin.site.register(Attempt, AttemptAdmin)
admin.site.register(SequenceItem, SequenceItemAdmin)
admin.site.register(LtiParameters, LtiParametersAdmin)
admin.site.register(UserModule, UserModuleAdmin)
