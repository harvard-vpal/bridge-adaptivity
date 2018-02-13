# coding: utf-8
from uuid import uuid4


class WithUniqueSlugMixin(object):
    """
    If field `unique_field_name` is empty - generate unique value for field and in any case save model.

    This mixin is a model mixin and should be used only with models.
    """

    unique_field_name = 'slug'

    def _generate_unique_slug(self):
        """
        Generate unique UUID4 slug for field and check there's no records in DB with such value.

        :return unique value for slug
        """
        while True:
            # loop until find unique value for slug
            uniq_val = uuid4()
            if not self.__class__.objects.filter(**{self.unique_field_name: uniq_val}).exists():
                # if value is unique - break
                break
        return uniq_val

    def save(self, *args, **kwargs):
        if not getattr(self, self.unique_field_name, None):
            uniq_val = self._generate_unique_slug()
            # if found unique slug - attach it to self and save instance
            setattr(self, self.unique_field_name, uniq_val)
        super(WithUniqueSlugMixin, self).save(*args, **kwargs)
