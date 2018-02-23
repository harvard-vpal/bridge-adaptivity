import logging

from django import forms
from django.forms import ModelForm

from module.models import (
    Activity, CollectionGroup, Course, GRADING_POLICY_CHOICES, GRADING_POLICY_NAME_TO_CLS, GradingPolicy
)

log = logging.getLogger(__name__)


class ActivityForm(ModelForm):
    required_css_class = 'required'

    advanced_fields = ['source_launch_url', 'source_name', 'source_context_id']

    class Meta:
        model = Activity
        exclude = ['collection', 'lti_consumer', 'points']
        widgets = {
            'stype': forms.HiddenInput(),
            'points': forms.HiddenInput(),
        }


class GroupForm(ModelForm):
    grading_policy_name = forms.ChoiceField(
        choices=GRADING_POLICY_CHOICES,
        required=True,
    )

    class Meta:
        model = CollectionGroup
        fields = 'name', 'description', 'owner', 'course', 'collections', 'engine', 'grading_policy_name'

    def clean(self):
        super(GroupForm, self).clean()
        engine, policy = self.cleaned_data.get('engine'), self.cleaned_data.get('grading_policy_name')

        engine_cls = engine.engine_driver
        policy_cls = GRADING_POLICY_NAME_TO_CLS.get(policy)

        if policy_cls is None:
            raise forms.ValidationError({'grading_policy_name': ['Not correct policy']})

        required_engine = policy_cls.require.get('engine')

        if required_engine and not isinstance(engine_cls, required_engine):
            required_engine_names = ", ".join([e.__name__.strip('Engine') for e in required_engine])
            engine_err_msg = 'This Engine doesn\'t support chosen Policy. Please choose another policy or engine.'
            policy_err_msg = 'This policy can be used only with {} engine(s). Choose another policy or engine.'.format(
                required_engine_names,
            )
            raise forms.ValidationError({'engine': [engine_err_msg], 'grading_policy_name': [policy_err_msg]})
        return self.cleaned_data


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
