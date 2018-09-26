from django.conf import settings
from django.test import TestCase
from mock import patch

from bridge_lti.models import BridgeUser, LtiProvider, LtiUser
from module import tasks
from module.models import Activity, Collection, CollectionGroup, CollectionOrder, Engine, GradingPolicy, Sequence
from module.tasks import sync_collection_engines


class TestTask(TestCase):
    def setUp(self):
        self.user = BridgeUser.objects.create_user(
            username='test_instructor',
            password='testtest',
            email='test_instructor@example.com'
        )
        self.consumer = LtiProvider.objects.create(
            consumer_name='name',
            consumer_key='key',
            consumer_secret='secret',
        )
        self.lti_user = LtiUser.objects.create(
            user_id='some_user',
            course_id='some_course',
            email=self.user.email,
            lti_consumer=self.consumer,
            bridge_user=self.user,
        )
        self.engine = Engine.objects.create(engine='engine_mock', engine_name='mock_eng')
        self.grading_policy = GradingPolicy.objects.create(name='full_credit', public_name='test_sequence_policy')
        self.collection_group = CollectionGroup.objects.create(
            name='col_group', owner=self.user, engine=self.engine, grading_policy=self.grading_policy
        )

    @patch('module.tasks.sync_collection_engines.apply_async')
    @patch('module.engines.engine_mock.EngineMock.sync_collection_activities')
    def test_collection_engine_sync(self, mock_sync_collection_activities, mock_apply_async):
        collection = Collection.objects.create(name='test_col', owner=self.user)
        mock_apply_async.assert_called_once_with(
            kwargs={'collection_slug': collection.slug, 'created_at': collection.updated_at},
            countdown=settings.CELERY_DELAY_SYNC_TASK,
        )

        CollectionOrder.objects.create(group=self.collection_group, collection=collection)

        self.activity = Activity.objects.create(name='testA1', collection=collection)
        mock_apply_async.assert_called_with(
            kwargs={'collection_slug': collection.slug, 'created_at': collection.updated_at},
            countdown=settings.CELERY_DELAY_SYNC_TASK,
        )
        sync_collection_engines(collection_slug=collection.slug, created_at=collection.updated_at)
        mock_sync_collection_activities.assert_called_once_with(collection)

    @patch('module.tasks.sync_collection_engines.apply_async')
    @patch('module.policies.base.BaseGradingPolicy.send_grade')
    def test_update_students_grades(self, mock_send_grade, mock_apply_async):
        collection = Collection.objects.create(name='test_col', owner=self.user)

        CollectionOrder.objects.create(group=self.collection_group, collection=collection)

        Sequence.objects.create(
            lti_user=self.lti_user,
            collection=collection,
            group=self.collection_group,
            suffix='12345',
            lis_result_sourcedid='fake_lis_result_sourcedid',
        )
        tasks.update_students_grades(self.collection_group.id)
        mock_send_grade.assert_called_once_with()
