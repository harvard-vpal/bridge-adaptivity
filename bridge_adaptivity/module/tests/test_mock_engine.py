# coding: utf-8
from ddt import data, ddt, unpack
from django.test import TestCase
from mock.mock import patch

from bridge_lti.models import LtiLmsPlatform, LtiUser
from module.models import (
    Activity, BridgeUser, Collection, CollectionOrder, Engine, GradingPolicy, ModuleGroup, Sequence, SequenceItem
)


@ddt
class TestMockEngine(TestCase):
    fixtures = ['gradingpolicy.json', 'engine.json']

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        self.user = BridgeUser.objects.create_user(
            username='test',
            password='test',
            email='test@me.com'
        )
        self.lms_platform = LtiLmsPlatform.objects.create(
            consumer_name='name',
            consumer_key='key',
            consumer_secret='secret',
        )
        self.lti_user = LtiUser.objects.create(
            user_id='some_user', course_id='some_course', email=self.user.email,
            lti_lms_platform=self.lms_platform, bridge_user=self.user
        )
        # collections
        self.collection1 = Collection.objects.create(name='col1', owner=self.user)
        # grading policies
        self.trials_count = GradingPolicy.objects.get(name='trials_count')
        self.points_earned = GradingPolicy.objects.get(name='points_earned')
        self.engine = Engine.objects.create(engine='engine_mock')
        self.test_cg = ModuleGroup.objects.create(
            name='TestColGroup',
            owner=self.user,
        )
        self.collection_order = CollectionOrder.objects.create(
            group=self.test_cg,
            collection=self.collection1,
            engine=self.engine,
            grading_policy=self.points_earned
        )
        self.sequence = Sequence.objects.create(
            lti_user=self.lti_user, collection_order=self.collection_order
        )

    @unpack
    @data({'activities': [{'stype': 'video', 'source_launch_url': 'http://source.url/{}'}],
           'sequence_items': [{'score': None}], 'er': None},
          {'activities': [{'stype': 'html', 'source_launch_url': 'http://source.url/{}'}],
           'sequence_items': [{'score': None}], 'er': None},
          {'activities': [{'stype': 'problem', 'source_launch_url': 'http://source.url/{}'}],
           'sequence_items': [{'score': None}], 'er': None},

          {'activities': [{'stype': 'problem', 'source_launch_url': 'http://source.url/{}', 'repetition': 2}],
          'sequence_items': [{'score': 1}], 'er': '__activity__'},

          {'activities': [{'stype': 'video', 'source_launch_url': 'http://source.url/{}'}] * 4,
          'sequence_items': [{'score': None}], 'er': "__activity__"},
          {'activities': [{'stype': 'html', 'source_launch_url': 'http://source.url/{}'}] * 4,
          'sequence_items': [{'score': None}], 'er': "__activity__"},
          {'activities': [{'stype': 'problem', 'source_launch_url': 'http://source.url/{}'}] * 4,
          'sequence_items': [{'score': None}], 'er': "__activity__"},
          )
    @patch('module.tasks.sync_collection_engines.apply_async')
    def test_create_sequence_item_for_activity(
        self, mock_apply_async, activities, sequence_items, er
    ):
        created_activities = []
        for i, activity in enumerate(activities):
            _activity = activity.copy()
            _activity['source_launch_url'] = activity['source_launch_url'].format(i)
            created_activities.append(Activity.objects.create(
                name='test_{}'.format(i), collection=self.collection1, tags='test', **_activity
            ))

        source_launch_urls = Activity.objects.values_list('source_launch_url', flat=True)

        for i, item in enumerate(sequence_items):
            SequenceItem.objects.create(
                sequence=self.sequence,
                activity=created_activities[i],
                **item
            )
        selected_activity_url = self.engine.engine_driver.select_activity(self.sequence).get('source_launch_url')

        if er == '__activity__':
            self.assertIsInstance(selected_activity_url, (str, str))
            self.assertTrue(selected_activity_url in source_launch_urls)
        else:
            self.assertEqual(selected_activity_url, er)
