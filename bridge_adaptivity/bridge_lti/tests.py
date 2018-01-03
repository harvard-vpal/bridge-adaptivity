import logging

from django.conf import settings
from django.http.response import Http404
from django.test import TestCase
from django.test.client import RequestFactory
import mock
from mock import Mock
import pytest


from .provider import learner_flow

log = logging.getLogger(__name__)


class RaisedExceptionUsesCustomTemplateTest(TestCase):
    def setUp(self):
        settings.DEBUG = False
        self.rf = RequestFactory()
        self.url = '/lti/launch/1'

    def test_learner_flow_with_incorrect_collection_id_test(self):
        """Check if learner_flow function is called with incorrect collection_id raise proper exception."""
        request = self.rf.post(self.url)
        with pytest.raises(Http404):
            learner_flow(
                request,
                lti_consumer=None,
                tool_provider=None,
                collection_id=1000
            )

    @mock.patch('lti.contrib.django.DjangoToolProvider.from_django_request')
    def test_client_post_with_incorrect_collection_id_test(self, from_django_request):
        """Test that when POST request received with not correct data it will show 404 error with correct template."""
        is_valid_request = Mock(return_value=False)
        tool_provider = Mock(is_valid_request=is_valid_request)
        from_django_request.return_value = tool_provider

        response = self.client.post(self.url)
        self.assertTemplateUsed(response, '404.html')
        from_django_request.assert_called_once()
        tool_provider.is_valid_request.assert_called_once()
