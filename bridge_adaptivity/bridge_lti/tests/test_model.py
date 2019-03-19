from django.core.exceptions import ValidationError
import pytest

from api.models import OAuthClient
from bridge_lti.models import LtiContentSource
from module.tests.test_views import BridgeTestCase


class BridgeLtiModelTest(BridgeTestCase):
    """
    Tests for the bridge_lti models.
    """

    def test_content_source_validation(self):
        """
        Test that LtiContentSource has correct validators.
        """
        base_args = {
            'name': 'some_name',
            'provider_key': 'provider_key',
            'provider_secret': 'provider_secret',
            'host_url': 'https://example.com/',
        }
        with pytest.raises(ValidationError):
            LtiContentSource(
                **base_args,
                source_type=LtiContentSource.EDX_SOURCE
            ).clean()

        LtiContentSource(
            **base_args,
            source_type=LtiContentSource.EDX_SOURCE,
            o_auth_client=OAuthClient()
        ).clean()

        LtiContentSource(
            **base_args,
            source_type=LtiContentSource.BASE_SOURCE,
        ).clean()
