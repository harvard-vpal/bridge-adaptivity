from ddt import data, ddt, unpack
from django.test import TestCase
from mock.mock import patch

from bridge_lti.models import LtiLmsPlatform, LtiUser, OutcomeService
from common.utils import find_last_sequence_item
from module.models import (
    Activity, BridgeUser, Collection, CollectionOrder, Engine, GradingPolicy, ModuleGroup, Sequence, SequenceItem
)


@ddt
class TestSequence(TestCase):
    fixtures = ['gradingpolicy.json', 'engine.json']

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        self.user = BridgeUser.objects.create_user(
            username='test_user',
            password='test_pass',
            email='test@test.com'
        )
        self.collection = Collection.objects.create(name='testcol1', owner=self.user)

        self.source_launch_url = 'http://test_source_launch_url.com'
        self.activity = Activity.objects.create(
            name='testactivity1', collection=self.collection, source_launch_url=self.source_launch_url
        )
        self.activity2 = Activity.objects.create(
            name='testactivity2',
            collection=self.collection,
            source_launch_url=f"{self.source_launch_url}2",
            stype='problem',
        )
        self.activity3 = Activity.objects.create(
            name='testactivity3', collection=self.collection, source_launch_url=f"{self.source_launch_url}3",
        )
        self.activity4 = Activity.objects.create(
            name='testactivity4',
            collection=self.collection,
            source_launch_url=f"{self.source_launch_url}4",
            stype='problem',
        )
        self.activity5 = Activity.objects.create(
            name='testactivity5',
            collection=self.collection,
            source_launch_url=f"{self.source_launch_url}5",
            stype='problem',
        )
        self.lti_lms_platform = LtiLmsPlatform.objects.create(
            consumer_name='test_consumer', consumer_key='test_consumer_key', consumer_secret='test_consumer_secret'
        )
        self.lti_user = LtiUser.objects.create(
            user_id='test_user_id', lti_lms_platform=self.lti_lms_platform, bridge_user=self.user
        )
        self.engine = Engine.objects.get(engine='engine_mock')
        self.grading_policy = GradingPolicy.objects.get(name='points_earned')
        self.outcome_service = OutcomeService.objects.create(
            lis_outcome_service_url='test_url', lms_lti_connection=self.lti_lms_platform
        )

        self.test_cg = ModuleGroup.objects.create(
            name='TestColGroup',
            owner=self.user,
        )

        self.collection_order = CollectionOrder.objects.create(
            group=self.test_cg,
            collection=self.collection,
            engine=self.engine,
            grading_policy=self.grading_policy
        )

        self.sequence = Sequence.objects.create(
            lti_user=self.lti_user,
            collection_order=self.collection_order,
            outcome_service=self.outcome_service
        )
        self.sequence_item_1 = SequenceItem.objects.create(sequence=self.sequence, activity=self.activity, score=0.4)
        self.sequence_item_2 = SequenceItem.objects.create(sequence=self.sequence, activity=self.activity2, score=0.6)
        self.sequence_item_3 = SequenceItem.objects.create(sequence=self.sequence, activity=self.activity3)
        self.sequence_item_4 = SequenceItem.objects.create(sequence=self.sequence, activity=self.activity4)

    @unpack
    @data(
        {'strict_forward': True, 'expected_item_index': 3},
        {'strict_forward': False, 'expected_item_index': 4},
    )
    def test_find_last_sequence_item(self, strict_forward, expected_item_index):
        expected_result = getattr(self, f"sequence_item_{expected_item_index}")
        result = find_last_sequence_item(self.sequence, strict_forward)
        self.assertEqual(expected_result, result)
