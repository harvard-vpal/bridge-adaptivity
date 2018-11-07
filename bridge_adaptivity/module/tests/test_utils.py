import logging

import ddt
from django.core.exceptions import MultipleObjectsReturned
from django.test import TestCase
from mock import patch

from bridge_lti.models import BridgeUser, LtiProvider, LtiUser, OutcomeService
from module.models import (
    Activity, Collection, CollectionGroup, CollectionOrder, Engine, GradingPolicy, Sequence, SequenceItem,
)
from module.utils import choose_activity, select_next_sequence_item

log = logging.getLogger(__name__)


@ddt.ddt
class TestUtilities(TestCase):
    fixtures = ['gradingpolicy', 'engine']

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        self.user = BridgeUser.objects.create_user(
            username='test_user',
            password='test_pass',
            email='test@test.com'
        )
        self.collection = Collection.objects.create(name='testcol1', owner=self.user)
        self.collection2 = Collection.objects.create(name='testcol2', owner=self.user)

        self.source_launch_url = 'http://test_source_launch_url.com'
        self.activity = Activity.objects.create(
            name='testactivity1', collection=self.collection, source_launch_url=self.source_launch_url
        )
        self.activity2 = Activity.objects.create(
            name='testactivity2', collection=self.collection2, source_launch_url=self.source_launch_url
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
        self.lti_provider = LtiProvider.objects.create(
            consumer_name='test_consumer', consumer_key='test_consumer_key', consumer_secret='test_consumer_secret'
        )
        self.lti_user = LtiUser.objects.create(
            user_id='test_user_id', lti_consumer=self.lti_provider, bridge_user=self.user
        )
        self.engine = Engine.objects.get(engine='engine_mock')
        self.gading_policy = GradingPolicy.objects.get(name='trials_count')
        self.outcome_service = OutcomeService.objects.create(
            lis_outcome_service_url='test_url', lms_lti_connection=self.lti_provider
        )

        self.test_cg = CollectionGroup.objects.create(
            name='TestColGroup',
            owner=self.user,
            engine=self.engine,
            grading_policy=self.gading_policy
        )

        CollectionOrder.objects.create(group=self.test_cg, collection=self.collection)

        self.sequence = Sequence.objects.create(
            lti_user=self.lti_user,
            collection=self.collection,
            group=self.test_cg,
        )
        self.vpal_engine = Engine.objects.get(engine='engine_vpal')

        self.vpal_group = CollectionGroup.objects.create(
            name='TestVpalGroup',
            owner=self.user,
            engine=self.vpal_engine,
        )

        CollectionOrder.objects.create(group=self.vpal_group, collection=self.collection)

        self.vpal_sequence = Sequence.objects.create(
            lti_user=self.lti_user,
            collection=self.collection,
            group=self.vpal_group,
            outcome_service=self.outcome_service
        )
        self.sequence_item_1 = SequenceItem.objects.create(sequence=self.sequence, activity=self.activity, score=0.4)
        self.sequence_item_2 = SequenceItem.objects.create(
            sequence=self.sequence, activity=self.activity2, score=0.6, position=2
        )
        self.sequence_item_3 = SequenceItem.objects.create(sequence=self.sequence, activity=self.activity3, position=3)
        self.sequence_item_4 = SequenceItem.objects.create(sequence=self.sequence, activity=self.activity4, position=4)

    def test_choose_activity(self):
        try:
            # test if 2 activities has the same launch url but has different collections
            # this method should return only one activity, filtered by sequence.collection
            chosen_activity = choose_activity(sequence=self.sequence)
        except MultipleObjectsReturned as e:
            log.error(Activity.ojbects.all().values('collection', 'source_launch_url'))
            self.fail(e)
        expected_activity = Activity.objects.get(
            collection=self.sequence.collection, source_launch_url=f"{self.source_launch_url}5"
        )
        self.assertEqual(chosen_activity, expected_activity)

    @patch('module.engines.engine_vpal.EngineVPAL.select_activity', return_value=None)
    def test_choose_activity_with_unconfigured_engine(self, mock_choose_activity_by_engine):
        """
        Test sequence is deleted if after creating first activity is not chosen for any reason.
        """
        choose_activity(sequence=self.vpal_sequence)
        sequence_is_exists = Sequence.objects.filter(group=self.vpal_group)
        self.assertFalse(sequence_is_exists)

    @patch('module.engines.engine_vpal.EngineVPAL.select_activity', return_value={'complete': True})
    def test_choose_activity_from_completed_collection(self, mock_choose_activity_by_engine):
        """
        Test sequence becomes completed if at least one sequence_item exists and there no new activity chosen.
        """
        sequence_item = SequenceItem.objects.create(sequence=self.vpal_sequence, activity=self.activity)
        choose_activity(sequence_item=sequence_item)
        completed_sequence = Sequence.objects.filter(group=self.vpal_group).first()
        self.assertEqual(completed_sequence, self.vpal_sequence)
        self.assertTrue(completed_sequence.completed)

    @ddt.unpack
    @ddt.data(
        {
            'item_index': 1,
            'update_activity': False,
            'last_item': 4,
            'position': 2,
            'pre_expected_result': (2, None, None)
        },
        {
            'item_index': 3,
            'update_activity': False,
            'last_item': 4,
            'position': 4,
            'pre_expected_result': (4, None, None)
        },
        {
            'item_index': 3,
            'update_activity': True,
            'last_item': 4,
            'position': 4,
            'pre_expected_result': (5, None, None)
        },
        {
            'item_index': 4,
            'update_activity': False,
            'last_item': 4,
            'position': 5,
            'pre_expected_result': (4, None, None)
        },
    )
    def test_select_next_sequence_item(self, item_index, update_activity, last_item, position, pre_expected_result):
        next_item = getattr(self, f"sequence_item_{pre_expected_result[0]}", None)
        result = select_next_sequence_item(
            getattr(self, f"sequence_item_{item_index}"),
            update_activity,
            last_item,
            position,
        )
        if position > last_item or update_activity:
            next_item = self.sequence.items.last()
        expected_result = (next_item, *pre_expected_result[1:])
        self.assertEqual(expected_result, result)

    def test_sequence_completed_in_select_next_sequence_item(self):
        self.sequence_item_5 = SequenceItem.objects.create(sequence=self.sequence, activity=self.activity5, position=5)
        sequence_item = self.sequence_item_5
        expected_result = (sequence_item, True, None)
        result = select_next_sequence_item(sequence_item, update_activity=False, last_item=5, position=6)
        self.assertEqual(expected_result, result)
