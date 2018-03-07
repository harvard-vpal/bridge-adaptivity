

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
        return super(ModelFieldIsDefaultMixin, self).save(*args, **kwargs)
