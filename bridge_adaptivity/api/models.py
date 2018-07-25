from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import fields
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class OAuthClient(models.Model):
    """
    Model to manage OAuth API of content source providers.

    Content source API connections.
    """

    # Note (braiko) commented grant types are types that can exist, but now not used.
    AUTH_CODE = "code"
    # IMPLICIT = "implicit"
    # PASSWORD = "password"
    CREDENTIALS = "credentials"
    GRANT_TYPES = (
        (AUTH_CODE, 'authorization code'),
        # (IMPLICIT, 'implicit'),
        # (PASSWORD, 'resource owner password-based'),
        (CREDENTIALS, 'client credentials'),
    )

    name = fields.CharField(max_length=255, blank=True, null=True, unique=True)
    client_id = models.CharField(max_length=255, blank=True, null=True)
    client_secret = models.CharField(max_length=255)
    grant_type = fields.CharField(
        choices=GRANT_TYPES, default=CREDENTIALS, max_length=255, null=True, blank=True,
        help_text='OAuth grant type which is used by OpenEdx API.'
    )

    class Meta:
        verbose_name = "OAuth Client"
        verbose_name_plural = "OAuth Clients"

    def clean(self):
        """
        Check is model valid.

        Rise validation exception when we try to set edx as a source type without a auth client
        """
        super().clean()
        if self.grant_type == self.CREDENTIALS and not self.client_id:
            raise ValidationError({'client_id': 'Client credentials needs client id'})

    def __str__(self):
        return '<OAuthClient: {}>'.format(self.name or self.client_id)
