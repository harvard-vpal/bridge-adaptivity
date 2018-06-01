

class ModelFieldIsDefaultMixin(object):
    IS_DEFAULT_FIELD = 'is_default'

    @classmethod
    def create_default(cls):
        pass

    @classmethod
    def get_default(cls):
        return (
            cls.objects.filter(**{cls.IS_DEFAULT_FIELD: True}).first() or
            cls.create_default()
        )

    def save(self, *args, **kwargs):
        if getattr(self, self.IS_DEFAULT_FIELD, None):
            default_qs = self.__class__.objects.filter(**{self.IS_DEFAULT_FIELD: True})
            if default_qs:
                default_qs.update(**{self.IS_DEFAULT_FIELD: False})
        return super().save(*args, **kwargs)


class HasLinkedSequenceMixin(object):
    """
    This mixin implement two methods `has_linked_active_sequences` and `has_linked_sequences`.

    These methods are used to understand that object (Group or Collection) has linked sequences.
    """

    def has_linked_sequences(self):
        """Indicate that collection group has linked sequences."""
        # sequence has link to group
        return self.sequence_set.exists()

    def has_linked_active_sequences(self):
        """Indicate that collection group has linked not finished sequences."""
        return self.sequence_set.filter(completed=False).exists()
