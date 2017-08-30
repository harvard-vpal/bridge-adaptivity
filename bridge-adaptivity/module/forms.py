from django.core.exceptions import ValidationError
from django.forms import ModelForm

from module.models import Activity, Collection


class ActivityForm(ModelForm):
    class Meta:
        model = Activity
        exclude = ['collection', 'lti_consumer']


class CollectionForm(ModelForm):
    class Meta:
        model = Collection
        exclude = ['owner']

    def full_clean(self):
        super(CollectionForm, self).full_clean()
        try:
            self.instance.validate_unique()
        except ValidationError as exc:
            self._update_errors(exc)
