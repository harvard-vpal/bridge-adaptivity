# coding: utf-8
import datetime
from datetime import timedelta

from django.urls.base import reverse
from mock import patch

from bridge_lti.models import LtiConsumer
from module.tests.test_views import BridgeTestCase


class TestSourcesView(BridgeTestCase):
    fixtures = BridgeTestCase.fixtures + ['api.json', 'bridge.json']

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        super().setUp()

    @patch('api.backends.openedx.OpenEdxApiClient.get_oauth_access_token',
           return_value=('some_token', datetime.datetime.now() + timedelta(days=1)))
    @patch('api.backends.openedx.OpenEdxApiClient.get_course_blocks',
           return_value=[{'name': 'name'} for _ in range(10)])
    def test_get_course_blocks(self, mock_get_course_blocks, mock_get_oauth_access_token):
        """Should not raise exceptions if LtiConsumer count is 1."""
        url = reverse('api:sources')
        data = {
            'course_id': 'some_course_ID',
            'content_source_id': '2',
        }
        response = self.client.post(url, data)
        objects = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(objects), 10)

        LtiConsumer.objects.get(id=4).delete()

        response = self.client.post(url, data)
        new_objects = response.json()
        self.assertEqual(len(objects), len(new_objects))

    @patch('api.backends.openedx.OpenEdxApiClient.get_oauth_access_token',
           return_value=('some_token', datetime.datetime.now() + timedelta(days=1)))
    @patch('api.backends.openedx.OpenEdxApiClient.get_course_blocks',
           return_value=[{'name': 'name'} for _ in range(10)])
    def test_get_course_blocks_without_source_id(self, *mocks):
        """Should raise exception if LtiConsumer count is more than 1."""
        url = reverse('api:sources')
        data = {
            'course_id': 'some_course_ID',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)
