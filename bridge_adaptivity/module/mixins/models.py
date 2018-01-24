
class ModelFieldIsDefaultMixin(object):
    IS_DEFAULT_FIELD = 'is_default'

    def save(self, *args, **kwargs):
        if getattr(self, self.IS_DEFAULT_FIELD, None):
            default_qs = self.__class__.objects.filter(**{self.IS_DEFAULT_FIELD: True})
            if default_qs:
                default_qs.update(**{self.IS_DEFAULT_FIELD: False})
        return super(ModelFieldIsDefaultMixin, self).save(*args, **kwargs)
