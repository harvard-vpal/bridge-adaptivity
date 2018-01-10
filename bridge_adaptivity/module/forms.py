import logging

from django import forms
from django.conf import settings
from django.forms import ModelForm

from module.models import Activity, GradingPolicy, CollectionGroup

log = logging.getLogger(__name__)


class ActivityForm(ModelForm):
    required_css_class = 'required'

    class Meta:
        model = Activity
        exclude = ['collection', 'lti_consumer']


class GroupForm(ModelForm):
    grading_policy_name = forms.ChoiceField(
        choices=settings.GRADING_POLICIES,
        required=True,
        initial=lambda: GradingPolicy.objects.get(is_default=True).name
    )

    class Meta:
        model = CollectionGroup
        fields = 'name', 'owner', 'collections', 'engine', 'grading_policy_name'


class GradingPolicyForm(ModelForm):
    class Meta:
        model = GradingPolicy
        fields = 'threshold', 'name'
        widgets = {
            'name': forms.HiddenInput()
        }
