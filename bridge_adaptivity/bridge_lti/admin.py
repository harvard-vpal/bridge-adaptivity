from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.forms import ModelForm, ModelMultipleChoiceField
from django.utils.translation import ugettext_lazy as _

from .models import BridgeUser, LtiContentSource, LtiLmsPlatform, LtiUser, OutcomeService

admin.site.unregister(Group)


class GroupForm(ModelForm):
    """
    Form for updating ManyToMany related fields from the Group Admin object.
    """

    group_source = ModelMultipleChoiceField(
        label='Content Sources granted access',
        queryset=LtiContentSource.objects.all(),
        required=False,
        help_text='Content Sources which are available to the group',
        widget=admin.widgets.FilteredSelectMultiple('Content Sources', False)
    )
    user_set = ModelMultipleChoiceField(
        label='Users participated the group',
        queryset=BridgeUser.objects.all(),
        required=False,
        help_text='Bridge users (who are entered to the group)',
        widget=admin.widgets.FilteredSelectMultiple('bridge users', False)
    )


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    exclude = ['permissions']
    search_fields = ('name',)
    ordering = ('name',)
    fields = ('name', 'group_source', 'user_set')
    form = GroupForm

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == 'permissions':
            qs = kwargs.get('queryset', db_field.remote_field.model.objects)
            # Avoid a major performance hit resolving permission names which
            # triggers a content_type load:
            kwargs['queryset'] = qs.select_related('content_type')
        return super().formfield_for_manytomany(db_field, request=request, **kwargs)

    def save_model(self, request, obj, form, change):
        # save without m2m field (can't save them until obj has id)
        super().save_model(request, obj, form, change)
        # if that worked, deal with m2m field
        for field in ['group_source', 'user_set']:
            print(f'Field is {field}')
            getattr(obj, field).clear()
            for field_value in form.cleaned_data[field]:
                print(f'Trying adding chosen field: {field_value}')
                getattr(obj, field).add(field_value)

    def get_form(self, request, obj=None, **kwargs):
        for field in ['group_source', 'user_set']:
            if obj:
                self.form.base_fields[field].initial = [o.pk for o in getattr(obj, field).all()]
            else:
                self.form.base_fields[field].initial = []
        return super().get_form(request, obj, **kwargs)


@admin.register(LtiLmsPlatform)
class LtiLmsPlatformsAdmin(admin.ModelAdmin):
    exclude = ['expiration_date', 'lms_metadata']


@admin.register(LtiContentSource)
class LtiContentSourcesAdmin(admin.ModelAdmin):
    list_display = ('name', 'host_url', 'is_active',)
    list_editable = ('is_active',)
    filter_horizontal = ('available_in_groups',)


@admin.register(LtiUser)
class LtiUserAdmin(admin.ModelAdmin):
    pass


@admin.register(OutcomeService)
class OutcomeServiceAdmin(admin.ModelAdmin):
    pass


@admin.register(BridgeUser)
class BridgeUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'roles', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'roles', 'password1', 'password2'),
        }),
    )
    list_display = ('username', 'email', 'roles', 'first_name', 'last_name', 'is_staff')
