from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import fields
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from .utils import short_token


@python_2_unicode_compatible
class LtiProvider(models.Model):
    """
    Model to manage LTI consumers.

    LMS connections.
    Automatically generates key and secret for consumers.
    """

    consumer_name = models.CharField(max_length=255, unique=True)
    consumer_key = models.CharField(max_length=32, unique=True, default=short_token)  # index
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

    Content source connections.
    """

    name = fields.CharField(max_length=255, blank=True, null=True, unique=True)
    provider_key = models.CharField(max_length=255)
    provider_secret = models.CharField(max_length=255)
    lti_metadata = fields.CharField(max_length=255, null=True, blank=True)
    host_url = models.URLField(max_length=255, null=True)
    is_active = fields.BooleanField(default=False, help_text=_("Are its sources available for Instructors?"))

    class Meta:
        verbose_name = "LTI Consumer"
        verbose_name_plural = "LTI Consumers"

    def __str__(self):
        return '<LtiConsumer: {}>'.format(self.name or self.provider_key)

    def save(self, *args, **kwargs):
        if self.is_active:
            LtiConsumer.objects.filter(is_active=True).update(is_active=False)
        super(LtiConsumer, self).save(*args, **kwargs)


@python_2_unicode_compatible
class LtiUser(models.Model):
    """Model to manage LTI users."""

    user_id = fields.CharField(max_length=255)
    course_id = fields.CharField(max_length=255, blank=True, null=True)
    email = fields.CharField(max_length=255, blank=True, null=True)
    lti_consumer = models.ForeignKey('LtiProvider')
    bridge_user = models.ForeignKey('BridgeUser', blank=True, null=True)

    class Meta(object):
        verbose_name = "LTI User"
        verbose_name_plural = "LTI Users"
        unique_together = ('lti_consumer', 'user_id')

    def __str__(self):
        return '<LtiUser: {}>'.format(self.user_id)


@python_2_unicode_compatible
class BridgeUser(AbstractUser):
    """Bridge user based on the top of Django User."""

    roles = fields.CharField(
        max_length=255,
        help_text=_(
            'User <a target="_blank" href="https://www.imsglobal.org/specs/ltiv1p1p1/implementation-guide#toc-22">'
            'LTI roles</a> (comma separated).'
        )
    )

    class Meta:
        verbose_name = _('bridge user')
        verbose_name_plural = _('bridge users')

    def __str__(self):
        return '<BridgeUser: {}>'.format(self.username)


@python_2_unicode_compatible
class OutcomeService(models.Model):
    """
    Model for a single outcome service associated with an LTI consumer.

    Note that a given consumer may have more than one outcome service URL over its
    lifetime, so we need to store the outcome service separately from the SourceLtiConnection model.
    """

    lis_outcome_service_url = models.CharField(max_length=255)
    lms_lti_connection = models.ForeignKey('LtiProvider', null=True)

    class Meta:
        verbose_name = _('outcome service')
        verbose_name_plural = _('outcome services')

    def __str__(self):
        return '<OutcomeService: {}>'.format(self.lis_outcome_service_url)
