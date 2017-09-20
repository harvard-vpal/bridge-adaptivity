import logging

from django.forms import ModelForm

from module.models import Activity

log = logging.getLogger(__name__)


class ActivityForm(ModelForm):
    required_css_class = 'required'

    class Meta:
        model = Activity
        exclude = ['collection', 'lti_consumer']
