import datetime
from datetime import timedelta

from django.urls.base import reverse
from mock import patch

from api.backends.api_client import get_available_blocks, get_available_courses
from bridge_lti.models import LtiConsumer
from module.tests.test_views import BridgeTestCase


class TestSourcesView(BridgeTestCase):
    fixtures = BridgeTestCase.fixtures + ['api.json', 'bridge.json']

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        super().setUp()

    @patch('api.backends.edx_api_client.OpenEdxApiClient.get_oauth_access_token',
           return_value=('some_token', datetime.datetime.now() + timedelta(days=1)))
    @patch('api.backends.edx_api_client.OpenEdxApiClient.get_course_blocks',
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

    @patch('api.backends.edx_api_client.OpenEdxApiClient.get_provider_courses')
    @patch('api.backends.base_api_client.BaseApiClient.get_provider_courses')
    @patch('api.backends.edx_api_client.OpenEdxApiClient.get_course_blocks')
    @patch('api.backends.base_api_client.BaseApiClient.get_course_blocks')
    def test_base_api_client_calls(
            self,
            mock_base_get_course_blocks,
            mock_edx_get_course_blocks,
            mock_base_get_provider_courses,
            mock_edx_get_provider_courses
    ):
        """
        Check that get_course_blocks and get_provider_courses called from the correct place.

        We use the id of the content source equal to 5 because in fixture this source has type `base`
        """
        get_available_blocks(5)
        mock_base_get_course_blocks.assert_called_once()
        mock_edx_get_course_blocks.assert_not_called()

        get_available_courses(5)
        mock_base_get_provider_courses.assert_called_once()
        mock_edx_get_provider_courses.assert_not_called()

    @patch('api.backends.edx_api_client.OpenEdxApiClient.get_oauth_access_token',
           return_value=('some_token', datetime.datetime.now() + timedelta(days=1)))
    @patch('api.backends.edx_api_client.OpenEdxApiClient.get_provider_courses')
    @patch('api.backends.edx_api_client.OpenEdxApiClient.get_course_blocks')
    def test_base_edx_client_calls(
            self,
            mock_edx_get_course_blocks,
            mock_edx_get_provider_courses,
            mock_get_oauth_access_token
    ):
        """
        Check that get_course_blocks and get_provider_courses called from the edx api client.

        We use the id of the content source equal to 5 because in fixture this source has type `edx`
        """
        get_available_blocks(4)
        mock_edx_get_course_blocks.assert_called_once()

        get_available_courses(4)
        mock_edx_get_provider_courses.assert_called_once()

    @patch('api.backends.edx_api_client.OpenEdxApiClient.get_oauth_access_token',
           return_value=('some_token', datetime.datetime.now() + timedelta(days=1)))
    @patch('api.backends.edx_api_client.OpenEdxApiClient.get_course_blocks',
           return_value=[{'name': 'name'} for _ in range(10)])
    def test_get_course_blocks_without_source_id(self, *mocks):
        """Should raise exception if LtiConsumer count is more than 1."""
        url = reverse('api:sources')
        data = {
            'course_id': 'some_course_ID',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)
