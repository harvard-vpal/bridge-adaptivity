from django.db import models
from django.db.models import fields
from django.utils.encoding import python_2_unicode_compatible

from bridge_lti.models import LtiConsumer


@python_2_unicode_compatible
class OAuthClient(models.Model):
    """
    Model to manage OAuth API of content source providers.

    Content source API connections.
    """
    AUTH_CODE = "authorization code"
    IMPLICIT = "implicit"
    PASSWORD = "resource owner password-based"
    CREDENTIALS = "client credentials"
    GRANT_TYPES = (
        ('code', AUTH_CODE),
        ('implicit', IMPLICIT),
        ('password', PASSWORD),
        ('credentials', CREDENTIALS),
    )

    name = fields.CharField(max_length=255, blank=True, null=True, unique=True)
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    grant_type = fields.CharField(
        choices=GRANT_TYPES, default='credentials', max_length=255, null=True, blank=True,
        help_text='OAuth grant type which is used by OpenEdx API.'
    )
    content_provider = models.ForeignKey(LtiConsumer, null=True, related_name="oauth_clients")

    class Meta:
        verbose_name = "OAuth Client"
        verbose_name_plural = "OAuth Clients"

    def __str__(self):
        return '<OAuthClient: {}>'.format(self.name or self.client_id)
