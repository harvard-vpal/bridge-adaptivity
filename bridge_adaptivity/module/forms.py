from django.forms import ModelForm

from module.models import Activity


class ActivityForm(ModelForm):
    class Meta:
        model = Activity
        exclude = ['collection', 'lti_consumer']
