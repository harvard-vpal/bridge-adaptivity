from django.contrib.auth.models import AbstractUser, Permission, Group, User
from django.db import models
from django.db.models import fields
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from .utils import short_token


@python_2_unicode_compatible
class LtiProvider(models.Model):
    """
    Model to manage LTI consumers.

    This model stores the consumer specific settings, such as the OAuth key/secret pair and any LTI fields
    that must be persisted.
    Automatically generates key and secret for consumers.
    """
    consumer_name = models.CharField(max_length=255, unique=True)
    consumer_key = models.CharField(max_length=32, unique=True, default=short_token)
    consumer_secret = models.CharField(max_length=32, unique=True, default=short_token)
    expiration_date = models.DateField(verbose_name='Consumer key expiration date', null=True, blank=True)
    lms_metadata = fields.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = "LTI Provider"
        verbose_name_plural = "LTI Providers"

    def __str__(self):
        return '<LtiProvider: {}>'.format(self.consumer_name)


@python_2_unicode_compatible
class LtiConsumer(models.Model):
    """
    Model to manage LTI source providers.
    """
    name = fields.CharField(max_length=255, blank=True, null=True, unique=True)
    provider_key = models.CharField(max_length=255)
    provider_secret = models.CharField(max_length=255)
    lti_metadata = fields.CharField(max_length=255, null=True, blank=True)
    source_url = fields.URLField()

    class Meta:
        verbose_name = "LTI Consumer"
        verbose_name_plural = "LTI Consumers"

    def __str__(self):
        return '<LtiConsumer: {}>'.format(self.name if self.name else self.provider_key)


@python_2_unicode_compatible
class LtiUser(models.Model):
    """
    Model to manage LTI users.
    """
    user_id = fields.CharField(max_length=255)
    course_id = fields.CharField(max_length=255, blank=True, null=True)
    email = fields.CharField(max_length=255, blank=True, null=True)
    lti_consumer = models.ForeignKey('LtiProvider')
    bridge_user = models.ForeignKey('BridgeUser')

    class Meta(object):
        verbose_name = "LTI User"
        verbose_name_plural = "LTI Users"
        unique_together = ('lti_consumer', 'user_id')

    def __str__(self):
        return '<LtiUser: {}>'.format(self.user_id)


@python_2_unicode_compatible
class BridgeUser(AbstractUser):
    """
    Bridge user based on the top of Django User.
    """
    roles = fields.CharField(max_length=255)

    class Meta:
        verbose_name = _('bridge user')
        verbose_name_plural = _('bridge users')

    def __str__(self):
        return '<BridgeUser: {}>'.format(self.username)
