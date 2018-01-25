from django.conf import settings
from django.test import TestCase
from mock import patch

from bridge_lti.models import BridgeUser
from module.models import Activity, Collection, CollectionGroup, Engine
from module.tasks import sync_collection_engines


class TestTask(TestCase):
    def setUp(self):
        self.user = BridgeUser.objects.create_user(
            username='test_instructor',
            password='testtest',
            email='test_instructor@example.com'
        )
        self.engine = Engine.objects.create(engine='engine_mock', engine_name='mock_eng')
        self.collection_group = CollectionGroup.objects.create(name='col_group', owner=self.user, engine=self.engine)

    @patch('module.tasks.sync_collection_engines.apply_async')
    @patch('module.engines.engine_mock.EngineMock.sync_collection_activities')
    def test_collection_engine_sync(self, mock_sync_collection_activities, mock_apply_async):
        collection = Collection.objects.create(name='test_col', owner=self.user)
        mock_apply_async.assert_called_once_with(
            kwargs={'collection_id': collection.id, 'created_at': collection.updated_at},
            countdown=settings.CELERY_DELAY_SYNC_TASK,
        )
        self.collection_group.collections.add(collection)
        self.activity = Activity.objects.create(name='testA1', collection=collection)
        mock_apply_async.assert_called_with(
            kwargs={'collection_id': collection.id, 'created_at': collection.updated_at},
            countdown=settings.CELERY_DELAY_SYNC_TASK,
        )
        sync_collection_engines(collection_id=collection.id, created_at=collection.updated_at)
        mock_sync_collection_activities.assert_called_once_with(collection)
