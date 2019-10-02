"""
Forms to work with module's models.
"""
import logging

from django import forms
from django.conf import settings
from django.forms import ModelForm
from django.forms.widgets import HiddenInput
from django.utils.translation import ugettext_lazy as _

from bridge_lti.models import BridgeUser
from module.models import (
    Activity, Collection, CollectionOrder, ContributorPermission, GRADING_POLICY_NAME_TO_CLS, GradingPolicy, ModuleGroup
)
from module.widgets import PolicyChoiceWidget


log = logging.getLogger(__name__)


class ActivityForm(ModelForm):
    """
    Form to work with Activity models.
    """

    required_css_class = 'required'
    advanced_fields = ['source_launch_url', 'source_name', 'lti_content_source']

    class Meta:
        """
        Inner class with metadata options for ActivityForm.
        """

        model = Activity
        exclude = ['collection', 'points']
        widgets = {
            'stype': forms.HiddenInput(),
            'lti_lms_platform': forms.HiddenInput(),
            'difficulty': forms.NumberInput(attrs={'step': "0.1", "min": 0.0, "max": 1.0}),
        }


class ModuleGroupForm(ModelForm):
    """
    Form to work with ModuleGroup models.
    """

    class Meta:
        """
        Inner class with metadata options for ModuleGroupForm.
        """

        model = ModuleGroup
        fields = ('name', 'description', 'owner')


class BaseGradingPolicyForm(ModelForm):
    """
    Base form to work with GradingPolicy models.

    This is form has hidden input with GradingPolicy name.
    """

    class Meta:
        """
        Inner class with metadata options for BaseGradingPolicyForm.
        """

        model = GradingPolicy
        fields = 'name',
        widgets = {'name': forms.HiddenInput()}


class BaseCollectionForm(ModelForm):
    """
    Form to work with Collection models.

    This is form has hidden input with Collection owner.
    """

    class Meta:
        """
        Inner class with metadata options for BaseGradingPolicyForm.
        """

        model = Collection
        fields = ['name', 'metadata', 'owner']
        widgets = {'owner': forms.HiddenInput()}


class ThresholdGradingPolicyForm(ModelForm):
    """
    Threshold Form to work with GradingPolicy models.

    This is form has hidden input with GradingPolicy name and textarea with params in JSON format.
    """

    class Meta:
        """
        Inner class with metadata options for ThresholdGradingPolicyForm.
        """

        model = GradingPolicy
        fields = 'params', 'name'
        widgets = {'params': forms.Textarea(attrs={'rows': '2'}), 'name': forms.HiddenInput()}
        help_texts = {'params': '{"threshold": &lt;value&gt;} is required, please use JSON format.'}

    def clean(self):
        super().clean()
        policy_name, params = self.cleaned_data.get('name'), self.cleaned_data.get('params')
        required_params = GRADING_POLICY_NAME_TO_CLS.get(policy_name).require.get('params')
        if required_params:
            if params is None:
                params = self.cleaned_data['params'] = {}
            for param, default in required_params.items():
                if param not in params:
                    params[param] = default
                    continue
                # TODO(idegtiarov) `threshold` parameter validation is hardcoded.
                # It should be rewritten when some new parameter appears.
                if param == 'threshold':
                    try:
                        threshold = int(params[param])
                    except ValueError:
                        threshold = default
                    threshold = threshold if threshold > 0 else default
                    params[param] = threshold

        return self.cleaned_data


class CollectionOrderForm(ModelForm):
    """
    Add collection in group form.
    """

    grading_policy_name = forms.ChoiceField(
        choices=((k, v) for k, v in GRADING_POLICY_NAME_TO_CLS.items()),
        required=True,
        widget=PolicyChoiceWidget
    )

    class Meta:
        """
        Inner class with metadata options for CollectionOrderForm.
        """

        model = CollectionOrder
        fields = (
            'collection',
            'slug',
            'engine',
            'grading_policy_name',
            'strict_forward',
            'ui_option',
            'ui_next',
            'congratulation_message',
        )
        labels = {
            'ui_option': _('UI Option'),
            'ui_next': _('Additional NEXT Button'),
            'congratulation_message': _('Show congratulation message if score is {}%+').format(
                int(settings.CONGRATULATION_SCORE_LEVEL * 100)
            )
        }
        help_texts = {'collection': _(
            "You can choose the available collection or create a new Collection above."
        )}

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.group = kwargs.pop('group')
        read_only = kwargs.pop('read_only') if 'read_only' in kwargs else False
        super().__init__(*args, **kwargs)
        self.fields['collection'].queryset = self.fields['collection'].queryset.filter(
            owner_id=self.user.id
        )
        if read_only:
            self.fields['collection'].widget = HiddenInput()
            self.fields['collection'].widget.attrs['readonly'] = read_only

    def clean(self):
        super().clean()
        engine, policy = self.cleaned_data.get('engine'), self.cleaned_data.get('grading_policy_name')

        engine_cls = engine.engine_driver
        policy_cls = GRADING_POLICY_NAME_TO_CLS.get(policy)

        if policy_cls is None:
            raise forms.ValidationError({'grading_policy_name': ['Not correct policy']})

        required_engine = policy_cls.require.get('engine')

        if required_engine and not isinstance(engine_cls, required_engine):
            engine_err_msg = 'This Engine doesn\'t support chosen Policy. Please choose another policy or engine.'
            policy_err_msg = 'This policy can be used only with {} engine(s). Choose another policy or engine.'.format(
                ", ".join([engine.__name__.strip('Engine') for engine in required_engine])
            )
            raise forms.ValidationError({'engine': [engine_err_msg], 'grading_policy_name': [policy_err_msg]})
        return self.cleaned_data

    def save(self, **kwargs):
        self.instance.group = self.group
        self.instance.collection = self.cleaned_data['collection']
        self.instance.engine = self.cleaned_data['engine']
        self.instance.grading_policy = self.cleaned_data['grading_policy']
        self.instance.save()


class ContributorPermissionForm(ModelForm):
    """
    Share Module group to Bridge users.
    """

    contributor_username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Write a valid username'}))

    class Meta:
        """
        Inner class with metadata options for ContributorPermissionForm.
        """

        model = ModuleGroup
        fields = ('contributor_username',)

    def clean(self):
        super().clean()
        contributor_username = self.cleaned_data.get("contributor_username")
        new_consumer_obj = BridgeUser.objects.filter(username=contributor_username).first()
        if not new_consumer_obj:
            raise forms.ValidationError(
                {'contributor_username': "Username is not valid or Bridge user with this username is not exist"}
            )

        if self.instance.owner == new_consumer_obj:
            raise forms.ValidationError({
                'contributor_username': (
                    "You are already have got permission for this resource. You can share it with other Bridge users."
                )
            })

        if ContributorPermission.objects.filter(group=self.instance, user=new_consumer_obj).exists():
            raise forms.ValidationError(
                {'contributor_username': "User with this username already has got permission for this resource"}
            )

        self.cleaned_data["new_consumer_obj"] = new_consumer_obj

        return self.cleaned_data

    def save(self, **kwargs):
        permission = ContributorPermission.objects.create(
            group=self.instance, user=self.cleaned_data.get("new_consumer_obj")
        )
        permission.save()
