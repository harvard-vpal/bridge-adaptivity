"""
Test exceptions in LTI provider.
"""
import logging

from django.http.response import Http404
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.urls.base import reverse
import mock
from mock import Mock
import pytest


from bridge_lti.provider import learner_flow
from module.tests.test_views import BridgeTestCase

log = logging.getLogger(__name__)


class RaisedExceptionUsesCustomTemplateTest(BridgeTestCase):
    """
    Test incorrect working LTI provider.
    """

    def setUp(self):
        super().setUp()
        self.rf = RequestFactory()
        self.correct_kw = {'collection_order_slug': self.collection_order1.slug}
        self.not_correct_kw = {'collection_order_slug': self.collection_order1.slug + "_wrong"}
        self.url = reverse('lti:launch', kwargs=self.correct_kw)
        self.not_correct_url = reverse('lti:launch', kwargs=self.not_correct_kw)

    @override_settings(DEBUG=False)
    def test_learner_flow_with_incorrect_collection_order_slug(self):
        """
        Check if learner_flow function is called with incorrect collection_slug raise proper exception.
        """
        request = self.rf.post(self.url)
        with pytest.raises(Http404):
            learner_flow(
                request,
                lti_lms_platform=None,
                tool_provider=None,
                collection_order_slug=self.not_correct_kw["collection_order_slug"]
            )

    @mock.patch('lti.contrib.django.DjangoToolProvider.from_django_request')
    @override_settings(DEBUG=False)
    def test_client_post_with_incorrect_collection_order_slug_test(self, from_django_request):
        """
        Test that when POST request received with not correct data it will show 404 error with correct template.
        """
        is_valid_request = Mock(return_value=False)
        tool_provider = Mock(is_valid_request=is_valid_request)
        from_django_request.return_value = tool_provider

        response = self.client.post(self.not_correct_url)
        self.assertTemplateUsed(response, '404.html')
        from_django_request.assert_called_once()
        tool_provider.is_valid_request.assert_called_once()
