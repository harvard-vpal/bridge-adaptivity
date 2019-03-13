"""
Forms to work with module models.
"""
import logging

from django import forms
from django.forms import ModelForm
from django.forms.widgets import HiddenInput
from django.utils.translation import ugettext_lazy as _

from module.models import Activity, Collection, CollectionOrder, GRADING_POLICY_NAME_TO_CLS, GradingPolicy, ModuleGroup
from module.widgets import PolicyChoiceWidget

log = logging.getLogger(__name__)


class ActivityForm(ModelForm):
    """
    Form to work with Activity models.
    """

    required_css_class = 'required'
    advanced_fields = ['source_launch_url', 'source_name']

    class Meta:
        """
        Metaclass for ActivityForm.
        """

        model = Activity
        exclude = ['collection', 'points']
        widgets = {'stype': forms.HiddenInput(), 'points': forms.HiddenInput(), 'lti_consumer': forms.HiddenInput()}


class GroupForm(ModelForm):
    """
    Form to work with ModuleGroup(CollectionModule) models.
    """

    class Meta:
        """
        Metaclass for GroupForm.
        """

        model = ModuleGroup
        fields = ('name', 'description', 'owner', 'course', )


class BaseGradingPolicyForm(ModelForm):
    """
    Form to work with GradingPolicy models.

    This is form has hidden input with GradingPolicy name.
    """

    class Meta:
        """
        Metaclass for BaseGradingPolicyForm.
        """

        model = GradingPolicy
        fields = 'name',
        widgets = {'name': forms.HiddenInput()}


class BaseCollectionForm(ModelForm):
    """
    Form to work with GradingPolicy models.

    This is form has hidden input with GradingPolicy name.
    """

    class Meta:
        """
        Metaclass for BaseGradingPolicyForm.
        """

        model = Collection
        fields = ['name', 'slug', 'metadata', 'owner']
        widgets = {'owner': forms.HiddenInput()}


class ThresholdGradingPolicyForm(ModelForm):
    """
    Form to work with GradingPolicy models.

    This is form has hidden input with GradingPolicy name and textarea with params in JSON format.
    """

    class Meta:
        """
        Metaclass for ThresholdGradingPolicyForm.
        """

        model = GradingPolicy
        fields = 'params', 'name'
        widgets = {'params': forms.Textarea(attrs={'rows': '2'}), 'name': forms.HiddenInput()}
        help_texts = {'params': '{"threshold": &lt;value&gt;} is required, please use JSON format.'}

    def clean(self):
        """
        Make cleaned_data from Query.
        """
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
    """
    Add group to course form.
    """

    groups = forms.ModelMultipleChoiceField(
        label="Choose groups to add into this course:",
        queryset=ModuleGroup.objects.filter(course__isnull=True),
        widget=forms.CheckboxSelectMultiple()
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        self.course = kwargs.pop('course')
        super().__init__(*args, **kwargs)
        self.fields['groups'].queryset = self.fields['groups'].queryset.filter(owner_id=user.id)

    def save(self, **kwargs):
        """
        Save change that related to add groups to course.
        """
        group_ids = [group.id for group in self.cleaned_data['groups']]
        ModuleGroup.objects.filter(id__in=group_ids).update(course=self.course)


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
        Metaclass for CollectionOrderForm.
        """

        model = CollectionOrder
        fields = (
            'slug',
            'collection',
            'engine',
            'grading_policy_name',
            'strict_forward',
            'ui_option',
            'ui_next'
        )
        labels = {'ui_option': _('UI Option'), 'ui_next': _('Additional NEXT Button')}

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
        """
        Make cleaned_data from Query.
        """
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
        """
        Update CollectionOrder instance.
        """
        self.instance.group = self.group
        self.instance.collection = self.cleaned_data['collection']
        self.instance.engine = self.cleaned_data['engine']
        self.instance.grading_policy = self.cleaned_data['grading_policy']
        self.instance.save()
