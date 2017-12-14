from django.core.exceptions import SuspiciousOperation
from django.test import TestCase
from django.test.client import RequestFactory

import mock
from mock import Mock

import pytest
import logging
from django.conf import settings
from .provider import learner_flow

log = logging.getLogger(__name__)


class RaisedExceptionUsesCustomTemplateTest(TestCase):
    def setUp(self):
        settings.DEBUG = False
        self.rf = RequestFactory()
        self.url = '/lti/launch/1'

    def test_learner_flow_with_incorrect_collection_id_test(self):
        '''
        This test checks that when learner_flow were called with incorrect collection_id it will raise proper exception.
        '''
        request = self.rf.post(self.url)
        with pytest.raises(SuspiciousOperation):
            learner_flow(
                request,
                None,
                None,
                collection_id=1000
            )

    @mock.patch('lti.contrib.django.DjangoToolProvider.from_django_request')
    def test_client_post_with_incorrect_collection_id_test(self, from_django_request):
        is_valid_request = Mock(parent=from_django_request, return_value=False)
        tool_provider = Mock(return_value=is_valid_request)
        tool_provider.is_valid_request = Mock(return_value=False)
        from_django_request.return_value = tool_provider

        response = self.client.post(self.url)
        self.assertTemplateUsed(response, '404.html')
        from_django_request.assert_called_once()
        tool_provider.is_valid_request.assert_called_once()
