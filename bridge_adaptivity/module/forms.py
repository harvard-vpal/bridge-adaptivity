import logging

from django import forms
from django.forms import ModelForm
from django.forms.widgets import HiddenInput
from module.models import (
    Activity, Collection, CollectionGroup, CollectionOrder, GRADING_POLICY_CHOICES, GRADING_POLICY_NAME_TO_CLS,
    GradingPolicy,
)
from module.widgets import PolicyChoiceWidget

log = logging.getLogger(__name__)


class ActivityForm(ModelForm):
    required_css_class = 'required'

    advanced_fields = ['source_launch_url', 'source_name']

    class Meta:
        model = Activity
        exclude = ['collection', 'points']
        widgets = {
            'stype': forms.HiddenInput(),
            'points': forms.HiddenInput(),
            'lti_consumer': forms.HiddenInput(),
        }


class GroupForm(ModelForm):
    grading_policy_name = forms.ChoiceField(
        choices=GRADING_POLICY_CHOICES,
        required=True,
        widget=PolicyChoiceWidget
    )

    class Meta:
        model = CollectionGroup
        fields = (
            'name',
            'description',
            'owner',
            'course',
            #'collections',
            # 'engine',
            #'grading_policy_name',
            'ui_option',
            'ui_next',
        )
        labels = {
            'ui_option': 'UI Option', 'ui_next': 'Additional NEXT Button',
        }

    def clean(self):
        super().clean()
        # engine, policy = self.cleaned_data.get('engine'), self.cleaned_data.get('grading_policy_name')
        #
        # engine_cls = engine.engine_driver
        # policy_cls = GRADING_POLICY_NAME_TO_CLS.get(policy)
        #
        # if policy_cls is None:
        #     raise forms.ValidationError({'grading_policy_name': ['Not correct policy']})
        #
        # required_engine = policy_cls.require.get('engine')
        #
        # if required_engine and not isinstance(engine_cls, required_engine):
        #     required_engine_names = ", ".join([e.__name__.strip('Engine') for e in required_engine])
        #     engine_err_msg = 'This Engine doesn\'t support chosen Policy. Please choose another policy or engine.'
        #     policy_err_msg = 'This policy can be used only with {} engine(s). Choose another policy or engine.'.format(
        #         required_engine_names,
        #     )
        #     raise forms.ValidationError({'engine': [engine_err_msg], 'grading_policy_name': [policy_err_msg]})
        return self.cleaned_data

    def save(self):
        group = super().save(commit=False)
        group.save()
        # cleaned_collections = self.cleaned_data.get('collections', [])
        # initial_collections = self.initial.get('collections', [])
        # for collection in set(cleaned_collections) - set(initial_collections):
        #     CollectionOrder.objects.get_or_create(collection=collection, group=group)
        # for collection in set(initial_collections) - set(cleaned_collections):
        #     CollectionOrder.objects.filter(collection=collection, group=group).delete()
        return group


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
        fields = 'params', 'name'
        widgets = {
            'params': forms.Textarea(attrs={'rows': '2'}),
            'name': forms.HiddenInput(),
        }
        help_texts = {
            'params': '{"threshold": &lt;value&gt;} is required, please use JSON format.',
        }

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


class AddCourseGroupForm(forms.Form):
    """Add group to course form."""

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        self.course = kwargs.pop('course')
        super().__init__(*args, **kwargs)
        self.fields['groups'].queryset = self.fields['groups'].queryset.filter(owner_id=user.id)

    groups = forms.ModelMultipleChoiceField(
        label="Choose groups to add into this course:",
        queryset=CollectionGroup.objects.filter(course__isnull=True),
        widget=forms.CheckboxSelectMultiple()
    )

    def save(self, **kwargs):
        group_ids = [group.id for group in self.cleaned_data['groups']]
        CollectionGroup.objects.filter(id__in=group_ids).update(course=self.course)


class CollectionGroupForm(ModelForm):
    """Add collection in group form."""

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.group = kwargs.pop('group')
        read_only = kwargs.pop('read_only') if kwargs.get('read_only') else False
        super().__init__(*args, **kwargs)
        self.fields['collection'].queryset = self.fields['collection'].queryset.filter(
            owner_id=self.user.id
        )
        # if read_only:
        #     self.fields['collection'].widget = HiddenInput()
            #self.fields['collection'].widget.attrs['readonly'] = read_only


    # collections = forms.ModelMultipleChoiceField(
    #     label="Choose colections to add into this group:",
    #     queryset=Collection.objects.filter(),
    #     widget=forms.Select()
    # )

    grading_policy_name = forms.ChoiceField(
        choices=((k, v) for k, v in GRADING_POLICY_NAME_TO_CLS.items()),
        required=True,
        widget=PolicyChoiceWidget
    )

    class Meta:
        model = CollectionOrder
        fields = (
            'collection',
            'engine',
            'grading_policy_name',
        )

    def clean(self):
        super().clean()
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

    def save(self, **kwargs):
        self.instance.group = self.group
        self.instance.collection = self.cleaned_data['collection']
        self.instance.engine = self.cleaned_data['engine']
        self.instance.save()

