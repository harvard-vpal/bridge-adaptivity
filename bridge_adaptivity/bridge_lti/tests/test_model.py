from django.core.exceptions import ValidationError
import pytest

from api.models import OAuthClient
from bridge_lti.models import LtiContentSources
from module.tests.test_views import BridgeTestCase


class BridgeLtiModelTest(BridgeTestCase):
    """
    Tests for the bridge_lti models.
    """

    def test_content_source_validation(self):
        """
        Test that LtiContentSources has correct validators.
        """
        base_args = {
            'name': 'some_name',
            'provider_key': 'provider_key',
            'provider_secret': 'provider_secret',
            'host_url': 'https://example.com/',
        }
        with pytest.raises(ValidationError):
            LtiContentSources(
                **base_args,
                source_type=LtiContentSources.EDX_SOURCE
            ).clean()

        LtiContentSources(
            **base_args,
            source_type=LtiContentSources.EDX_SOURCE,
            o_auth_client=OAuthClient()
        ).clean()

        LtiContentSources(
            **base_args,
            source_type=LtiContentSources.BASE_SOURCE,
        ).clean()
