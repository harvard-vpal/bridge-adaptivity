from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import fields


class OAuthClient(models.Model):
    """
    Model to manage OAuth API of content source providers.

    Content source API connections.
    """

    AUTH_CODE = "code"
    CREDENTIALS = "credentials"
    GRANT_TYPES = (
        (AUTH_CODE, 'authorization code'),
        (CREDENTIALS, 'client credentials'),
    )

    name = fields.CharField(max_length=255, blank=True, null=True, unique=True)
    client_id = models.CharField(max_length=255, blank=True, null=True)
    client_secret = models.CharField(max_length=255)
    grant_type = fields.CharField(
        choices=GRANT_TYPES, default=CREDENTIALS, max_length=255, null=True, blank=True,
        help_text='OAuth grant type which is used by Client API.'
    )

    class Meta:
        verbose_name = "OAuth Client"
        verbose_name_plural = "OAuth Clients"

    def clean(self):
        """
        Check model is valid.

        Rise validation exception when the source type is set without an auth client.
        """
        super().clean()
        if self.grant_type == self.CREDENTIALS and not self.client_id:
            raise ValidationError({'client_id': 'Client credentials need client id'})

    def __str__(self):
        return '<OAuthClient: {}>'.format(self.name or self.client_id)
