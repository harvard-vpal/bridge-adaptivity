import datetime
from datetime import timedelta

from celery.exceptions import TimeoutError
from django.test import RequestFactory
from django.urls.base import reverse
from mock import patch

from api.backends.api_client import get_available_blocks, get_available_courses
from bridge_lti.models import LtiContentSource
from module.tests.test_views import BridgeTestCase


def mock_timeout(slug):
    if slug == 'col1':
        raise TimeoutError
    return []


class TestSourcesView(BridgeTestCase):
    fixtures = BridgeTestCase.fixtures + ['api.json', 'bridge.json']

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        super().setUp()
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.request.user = self.user

    @patch('api.backends.edx_api_client.OpenEdxApiClient.get_oauth_access_token',
           return_value=('some_token', datetime.datetime.now() + timedelta(days=1)))
    @patch('api.backends.edx_api_client.OpenEdxApiClient.get_course_blocks',
           return_value=[{'name': 'name'} for _ in range(10)])
    def test_get_course_blocks(self, mock_get_course_blocks, mock_get_oauth_access_token):
        """Should not raise exceptions if LtiContentSource count is 1."""
        url = reverse('api:sources')
        data = {
            'course_id': 'some_course_ID',
            'content_source_id': '2',
        }
        response = self.client.post(url, data)
        objects = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(objects), 10)

        LtiContentSource.objects.get(id=4).delete()

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
        get_available_blocks(self.request, 5)  # Second parameter is source id, which is taken from the fixtures
        mock_base_get_course_blocks.assert_called_once()
        mock_edx_get_course_blocks.assert_not_called()

        get_available_courses(self.request, 5)  # Second parameter is source id, which is taken from the fixtures
        mock_base_get_provider_courses.assert_called_once()
        mock_edx_get_provider_courses.assert_not_called()

    @patch(
        'api.backends.edx_api_client.OpenEdxApiClient.get_oauth_access_token',
        return_value=('some_token', datetime.datetime.now() + timedelta(days=1))
    )
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

        We use the id of the content source equal to 4 because in fixture this source has type `edx`
        """
        get_available_blocks(self.request, 4)  # Second parameter is source id, which is taken from the fixtures
        mock_edx_get_course_blocks.assert_called_once()

        get_available_courses(self.request, 4)  # Second parameter is source id, which is taken from the fixtures
        mock_edx_get_provider_courses.assert_called_once()

    @patch('api.backends.edx_api_client.OpenEdxApiClient.get_oauth_access_token',
           return_value=('some_token', datetime.datetime.now() + timedelta(days=1)))
    @patch('api.backends.edx_api_client.OpenEdxApiClient.get_course_blocks',
           return_value=[{'name': 'name'} for _ in range(10)])
    def test_get_course_blocks_without_source_id(self, *mocks):
        """Should raise exception if LtiContentSource count is more than 1."""
        url = reverse('api:sources')
        data = {
            'course_id': 'some_course_ID',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)

    @patch('module.views.tasks.sync_collection_engines')
    def test_sync_collection_success(self, mock_sync):
        mock_sync.delay().collect.return_value = [('Object', {"Mock": {"success": True}})]
        expected_data = {"engines": [{"Mock": {"success": True}}]}
        url = reverse('api:sync_collection', kwargs={'slug': self.collection1.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected_data)

    @patch('module.views.tasks.sync_collection_engines')
    def test_sync_collection_unsuccess(self, mock_sync):
        mock_sync.delay().collect.return_value = [
            ('Object', {"Mocker": {"success": True}}),
            ('Object', {"Mock": {"success": False, "message": "Message of error description"}}),
        ]
        expected_data = {"engines": [
            {"Mocker": {"success": True}},
            {"Mock": {"success": False, "message": "Message of error description"}},
        ]}
        url = reverse('api:sync_collection', kwargs={'slug': self.collection1.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected_data)

    @patch('module.views.tasks.sync_collection_engines')
    def test_sync_collection_timeout(self, mock_sync):
        expected_msg = 'Collection sync was failed, the reason is: TimeoutError'
        mock_sync.delay().collect.side_effect = TimeoutError
        url = reverse('api:sync_collection', kwargs={'slug': self.collection1.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, expected_msg)
