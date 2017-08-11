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

    class Meta:
        verbose_name = "LTI Consumer"
        verbose_name_plural = "LTI Consumers"

    def __str__(self):
        return '<LtiConsumer: {}>'.format(self.name or self.provider_key)


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
class LtiSource(models.Model):
    """
    Model to manage LTI content (materials).
    """
    lti_consumer = models.ForeignKey('LtiConsumer')
    launch_url = models.URLField(max_length=255, unique=True, null=True)
    name = fields.CharField(max_length=255, blank=True, null=True)
    course_id = fields.CharField(max_length=255, blank=True, null=True)

    class Meta(object):
        verbose_name = "LTI Source"
        verbose_name_plural = "LTI Sources"

    def __str__(self):
        return '<LtiSource : {} : {}>'.format(self.lti_consumer.name, self.name or self.id)
