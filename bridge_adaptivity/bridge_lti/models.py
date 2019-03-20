import logging

from django.contrib.auth import login
from django.contrib.auth.models import AbstractUser, Group
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import fields
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from api.models import OAuthClient
from .utils import short_token

log = logging.getLogger(__name__)


class LtiLmsPlatform(models.Model):
    """
    Model to manage LTI consumers.

    LMS connections.
    Automatically generates key and secret for consumers.
    """

    consumer_name = models.CharField(max_length=255, unique=True)
    consumer_key = models.CharField(max_length=32, unique=True, default=short_token, db_index=True)
    consumer_secret = models.CharField(max_length=32, unique=True, default=short_token)
    expiration_date = models.DateField(verbose_name='Consumer key expiration date', null=True, blank=True)
    lms_metadata = fields.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = "LMS Platform"
        verbose_name_plural = "LMS Platforms"

    def __str__(self):
        return '<LtiLmsPlatform: {}>'.format(self.consumer_name)


class LtiContentSource(models.Model):
    """
    Model to manage LTI source providers.

    Content source connections.
    """

    BASE_SOURCE = "base"
    EDX_SOURCE = "edx"
    DART = "dart"

    SOURCE_TYPE_CHOICES = (
        (BASE_SOURCE, "Base Source"),
        (EDX_SOURCE, "edX Source"),
        (DART, "Dart Source"),
    )

    name = fields.CharField(max_length=255, blank=True, null=True, unique=True)
    provider_key = models.CharField(max_length=255)
    provider_secret = models.CharField(max_length=255)
    lti_metadata = fields.CharField(max_length=255, null=True, blank=True)
    host_url = models.URLField(max_length=255, null=True)
    o_auth_client = models.ForeignKey('api.OAuthClient', default=None, null=True, blank=True, on_delete=models.CASCADE)
    is_active = fields.BooleanField(default=False, help_text=_("Are its sources available for Instructors?"))
    source_type = models.CharField(choices=SOURCE_TYPE_CHOICES, default=EDX_SOURCE, max_length=100)
    available_in_groups = models.ManyToManyField(Group, related_name='group_source', verbose_name='source in groups')

    class Meta:
        verbose_name = "Content Source"
        verbose_name_plural = "Content Sources"

    def __str__(self):
        return '<LtiContentSource: {}>'.format(self.name or self.provider_key)

    def clean(self):
        """
        Check is model valid.

        Rise validation exception when we try to set edx as a source type without a auth client
        """
        super().clean()
        if self.source_type == self.EDX_SOURCE and not self.o_auth_client:
            raise ValidationError({'o_auth_client': _('Edx content source needs OAuth client')})
        if self.source_type == self.EDX_SOURCE and self.o_auth_client.grant_type != OAuthClient.CREDENTIALS:
            raise ValidationError({'o_auth_client': _('Edx content source needs OAuth client with credentials type')})
        if self.source_type == self.DART and self.o_auth_client.grant_type != OAuthClient.AUTH_CODE:
            raise ValidationError({'o_auth_client': _('DART content source needs Auth client with grant type')})


class LtiUser(models.Model):
    """
    Model to manage LTI users.
    """

    user_id = fields.CharField(max_length=255, db_index=True)
    course_id = fields.CharField(max_length=255, blank=True, null=True)
    email = fields.CharField(max_length=255, blank=True, null=True)
    lti_lms_platform = models.ForeignKey('LtiLmsPlatform', on_delete=models.CASCADE)
    bridge_user = models.ForeignKey('BridgeUser', blank=True, null=True, on_delete=models.CASCADE)

    class Meta(object):
        verbose_name = "LTI User"
        verbose_name_plural = "LTI Users"
        unique_together = ('lti_lms_platform', 'user_id')

    def __str__(self):
        return '<LtiUser: {}>'.format(self.user_id)


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

    def login(self, request):
        """
        Login read-only bridge user.
        """
        self.backend = 'django.contrib.auth.backends.ModelBackend'
        log.debug(f"Bridge user backend User {self.backend} login process...")
        login(request, self)
        log.debug(f"Check User is authenticated: {request.user.is_authenticated}")


@receiver(post_save, sender=BridgeUser)
def add_user_to_default_group(sender, instance, created, **kwargs):
    """
    Post save signal handler for BridgeUser model.

    Add default group for every new BridgeUser.
    """
    if created:
        group, _ = Group.objects.get_or_create(name='Default')
        instance.groups.add(group)


class OutcomeService(models.Model):
    """
    Model for a single outcome service associated with an LTI consumer.

    Note that a given consumer may have more than one outcome service URL over its
    lifetime, so we need to store the outcome service separately from the SourceLtiConnection model.
    """

    lis_outcome_service_url = models.CharField(max_length=255)
    lms_lti_connection = models.ForeignKey('LtiLmsPlatform', null=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('outcome service')
        verbose_name_plural = _('outcome services')

    def __str__(self):
        return '<OutcomeService: {}>'.format(self.lis_outcome_service_url)
