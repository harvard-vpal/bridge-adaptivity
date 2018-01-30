import logging

from django import forms
from django.forms import ModelForm

from module.models import Activity, CollectionGroup, GRADING_POLICY_CHOICES, GradingPolicy

log = logging.getLogger(__name__)


class ActivityForm(ModelForm):
    required_css_class = 'required'

    class Meta:
        model = Activity
        exclude = ['collection', 'lti_consumer']


class GroupForm(ModelForm):
    grading_policy_name = forms.ChoiceField(
        choices=GRADING_POLICY_CHOICES,
        required=True,
    )

    class Meta:
        model = CollectionGroup
        fields = 'name', 'description', 'owner', 'collections', 'engine', 'grading_policy_name'


class BaseGradingPolicyForm(ModelForm):
    class Meta:
        model = GradingPolicy
        fields = 'name',
        widgets = {
            'name': forms.HiddenInput(),
        }


class ThresholdGradingPolicyForm(ModelForm):
    class Meta:
        model = GradingPolicy
        fields = 'threshold', 'name'
        widgets = {
            'name': forms.HiddenInput(),
        }
