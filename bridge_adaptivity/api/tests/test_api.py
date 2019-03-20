from django.urls import reverse
from mock import patch
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from bridge_lti.models import BridgeUser
from module.models import Activity, Collection


class TestApiBase(APITestCase):
    @classmethod
    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUpTestData(cls, mock_apply_async):
        cls.user = BridgeUser.objects.create(
            username='test',
            password='test',
        )
        cls.token = Token.objects.create(user=cls.user)
        cls.collection = Collection.objects.create(name='col1', owner=cls.user)
        cls.activity = Activity.objects.create(name='act1', collection=cls.collection, tags='test')

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)


class TestCollectionAPI(TestApiBase):
    """
    Test collection API endpoints.

    CRUD requests are tested as well as request authorization.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.list_url = reverse('api:collection-list')
        cls.detail_url = reverse('api:collection-detail', args=[cls.collection.id])

    def test_get_collection(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_api_collection_call_without_authorization(self):
        self.client.credentials()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 401)

    @patch('module.tasks.sync_collection_engines.apply_async')
    def test_update_collection(self, mock_apply_async):
        new_name = 'new_collection'
        data = {
            'name': new_name,
        }
        response = self.client.patch(self.detail_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], new_name)

    @patch('module.tasks.sync_collection_engines.apply_async')
    def test_create_collection(self, mock_apply_async):
        name = 'test_collection'
        data = {
            'name': name,
            'slug': f'{name}1',
            "metadata": None,
            "strict_forward": True,
            "owner": self.user.id
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], name)
        collections = self.client.get(self.list_url).data
        self.assertEqual(len(collections), 2)

    @patch('module.tasks.sync_collection_engines.apply_async')
    def test_delete_collection(self, mock_apply_async):
        name = 'test_collection'
        data = {
            'name': name,
            'slug': f'{name}1',
            "metadata": None,
            "strict_forward": True,
            "owner": self.user.id
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], name)
        deleted = self.client.delete(reverse('api:collection-detail', args=[response.data['id']]))
        self.assertEqual(deleted.status_code, 204)
        collections = self.client.get(self.list_url).data
        self.assertEqual(len(collections), 1)


class TestActivityAPI(TestApiBase):
    """
    Test activity API endpoints.

    CRUD requests are tested as well as request authorization.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.list_url = reverse('api:activity-list')
        cls.detail_url = reverse('api:activity-detail', args=[cls.activity.id])
        cls.name = 'test_activity'
        cls.data = {
            "name": cls.name,
            "tags": "test_tag",
            "atype": "G",
            "difficulty": 0.5,
            "points": 1.0,
            "source_launch_url": "http://testa.net/launch/url",
            "source_name": "",
            "stype": "",
            "collection": cls.collection.id,
            "lti_content_source": None
        }

    def test_get_activity(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_api_activity_call_without_authorization(self):
        self.client.credentials()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 401)

    @patch('module.tasks.sync_collection_engines.apply_async')
    def test_update_activity(self, mock_apply_async):
        new_name = 'new_activity'
        data = {
            'name': new_name,
        }
        response = self.client.patch(self.detail_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], new_name)

    @patch('module.tasks.sync_collection_engines.apply_async')
    def test_create_activity(self, mock_apply_async):
        response = self.client.post(self.list_url, self.data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], self.name)
        activities = self.client.get(self.list_url).data
        self.assertEqual(len(activities), 2)

    @patch('module.tasks.sync_collection_engines.apply_async')
    def test_delete_activity(self, mock_apply_async):
        response = self.client.post(self.list_url, self.data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], self.name)
        deleted = self.client.delete(reverse('api:activity-detail', args=[response.data['id']]))
        self.assertEqual(deleted.status_code, 204)
        activities = self.client.get(self.list_url).data
        self.assertEqual(len(activities), 1)
