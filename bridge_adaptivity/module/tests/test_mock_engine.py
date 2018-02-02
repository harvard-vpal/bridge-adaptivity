# coding: utf-8
from ddt import data, ddt, unpack
from django.test import TestCase
from mock.mock import patch

from bridge_lti.models import LtiProvider, LtiUser
from module.models import (
    Activity, BridgeUser, Collection, CollectionGroup, Engine, GradingPolicy, Sequence, SequenceItem
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
        self.consumer = LtiProvider.objects.create(
            consumer_name='name',
            consumer_key='key',
            consumer_secret='secret',
        )
        self.lti_user = LtiUser.objects.create(
            user_id='some_user', course_id='some_course', email=self.user.email,
            lti_consumer=self.consumer, bridge_user=self.user
        )
        self.client.login(username='test', password='test')
        # collections
        self.collection1 = Collection.objects.create(name='col1', owner=self.user)
        # grading policies
        self.trials_count = GradingPolicy.objects.get(name='trials_count')
        self.points_earned = GradingPolicy.objects.get(name='points_earned')
        self.engine = Engine.objects.create(engine='engine_mock')
        self.test_cg = CollectionGroup.objects.create(
            name='TestColGroup',
            owner=self.user,
            engine=self.engine,
            grading_policy=self.points_earned
        )
        self.test_cg.collections.add(self.collection1)
        self.sequence = Sequence.objects.create(
            lti_user=self.lti_user, collection=self.collection1,
            engine=self.engine, grading_policy=self.trials_count,
        )

    def test_check(self):
        self.assertTrue(True)

    @patch('module.tasks.sync_collection_engines.apply_async')
    @unpack
    @data({'activity': {'stype': 'video', 'atype': 'G', 'source_launch_url': 'http://source.url/{}'},
           'sequence_items': [{'score': None}], 'activity_count': 1, 'er': None},
          {'activity': {'stype': 'html', 'atype': 'G', 'source_launch_url': 'http://source.url/{}'},
           'sequence_items': [{'score': None}], 'activity_count': 1, 'er': None},
          {'activity': {'stype': 'problem', 'atype': 'G', 'source_launch_url': 'http://source.url/{}'},
           'sequence_items': [{'score': None}], 'activity_count': 1, 'er': '__activity__'},

          {'activity': {'stype': 'video', 'atype': 'G', 'source_launch_url': 'http://source.url/{}'},
          'sequence_items': [{'score': 1}], 'activity_count': 1, 'er': None},
          {'activity': {'stype': 'html', 'atype': 'G', 'source_launch_url': 'http://source.url/{}'},
          'sequence_items': [{'score': 1}], 'activity_count': 1, 'er': None},
          {'activity': {'stype': 'problem', 'atype': 'G', 'source_launch_url': 'http://source.url/{}'},
          'sequence_items': [{'score': 1}], 'activity_count': 1, 'er': None},

          {'activity': {'stype': 'video', 'atype': 'G', 'source_launch_url': 'http://source.url/{}'},
          'sequence_items': [{'score': None}], 'activity_count': 4, 'er': "__activity__"},
          {'activity': {'stype': 'html', 'atype': 'G', 'source_launch_url': 'http://source.url/{}'},
          'sequence_items': [{'score': None}], 'activity_count': 4, 'er': "__activity__"},
          {'activity': {'stype': 'problem', 'atype': 'G', 'source_launch_url': 'http://source.url/{}'},
          'sequence_items': [{'score': None}], 'activity_count': 4, 'er': "__activity__"},
          )
    def test_create_sequence_item_for_activity(self, mock_apply_async, activity,
                                               sequence_items, activity_count, er):
        activities = []
        for i in range(activity_count):
            _activity = activity.copy()
            _activity['source_launch_url'] = activity['source_launch_url'].format(i)
            activities.append(Activity.objects.create(
                name='test_{}'.format(i), collection=self.collection1, tags='test', **_activity
            ))

        source_launch_urls = Activity.objects.filter(
            id__in=[i.id for i in activities]
        ).values_list('source_launch_url', flat=True)

        created_sequence_items = []
        for i, item in enumerate(sequence_items):
            created_sequence_items.append(SequenceItem.objects.create(
                sequence=self.sequence,
                activity=activities[i],
                **item
            ))
        selected_activity_url = self.engine.engine_driver.select_activity(self.sequence)

        if er == '__activity__':
            self.assertIsInstance(selected_activity_url, (str, unicode))
            self.assertTrue(selected_activity_url in source_launch_urls)
        else:
            self.assertEqual(selected_activity_url, er)
