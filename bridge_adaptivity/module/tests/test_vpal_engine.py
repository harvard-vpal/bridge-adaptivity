import urlparse

from django.test import TestCase
from mock import Mock, patch

from bridge_lti.models import BridgeUser, LtiProvider, LtiUser
from module.engines import engine_vpal
from module.models import Activity, Collection, CollectionGroup, Engine, GradingPolicy, Sequence, SequenceItem


class TestVPALEngine(TestCase):
    fixtures = ['gradingpolicy', 'engine']

    @patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        self.engine = engine_vpal.EngineVPAL(HOST='test_host/', TOKEN='test-token')
        self.user = BridgeUser.objects.create_user(
            username='test',
            password='test',
            email='test@me.com'
        )
        self.collection = Collection.objects.create(name='test_col', owner=self.user)
        self.a1 = Activity.objects.create(
            name='act1',
            collection=self.collection,
            source_launch_url='test_url_act1',
            stype='html',
        )
        self.a2 = Activity.objects.create(
            name='act2',
            collection=self.collection,
            source_launch_url='test_url_act2',
            stype='problem',
        )
        self.lti_consumer = LtiProvider.objects.create(
            consumer_name='test_consumer_name',
            consumer_key='test_consumer_key',
            consumer_secret='test_consumer_secret',
        )
        self.lti_user = LtiUser.objects.create(
            user_id='test_ltiuser_id',
            lti_consumer=self.lti_consumer,
        )
        self.engine = Engine.objects.create(engine='engine_vpal', lti_parameters=' lis_person_sourcedid, lis_unknown')
        self.grading_policy = GradingPolicy.objects.create(name='trials_count', public_name='test_policy')

        self.group = CollectionGroup.objects.create(
            engine=self.engine, grading_policy=self.grading_policy, name='test-group', owner=self.user
        )
        self.group.collections.add(self.collection)

        self.sequence = Sequence.objects.create(
            lti_user=self.lti_user,
            collection=self.collection,
            group=self.group
        )
        self.sequence_item_1 = SequenceItem.objects.create(sequence=self.sequence, activity=self.a1, score=0.4)
        self.sequence_item_2 = SequenceItem.objects.create(sequence=self.sequence, activity=self.a2, score=0.6)

    def test_fulfill_payload(self):
        expected = {'activity': self.a1.source_launch_url, 'score': self.sequence_item_1.score, 'is_problem': False}
        payload = self.engine.engine_driver.fulfill_payload(instance_to_parse=self.sequence_item_1)
        self.assertEqual(payload, expected)

    @patch('requests.post', return_value=Mock(status_code=200))
    def test_select_activity(self, mock_post):
        expected_source_url = 'new_activity_source_url'
        lti_param = "lis_person_sourcedid"
        launch_params = {lti_param: "test_lis_person_sourcedid"}
        self.sequence.fulfil_sequence_metadata(self.engine.lti_params, launch_params)
        test_url = urlparse.urljoin(
            "{}/".format(self.engine.engine_driver.activity_url), "recommend"
        )
        expected_payload = {
            "learner": self.sequence.lti_user.id,
            "collection": self.sequence.collection.id,
            lti_param: self.sequence.metadata[lti_param],
            "sequence": [
                {
                    'activity': self.a1.source_launch_url,
                    'score': self.sequence_item_1.score,
                    'is_problem': False
                },
                {
                    'activity': self.a2.source_launch_url,
                    'score': self.sequence_item_2.score,
                    'is_problem': True
                },
            ]
        }
        response = mock_post.return_value
        response.json.return_value = {'source_launch_url': expected_source_url}
        result = self.engine.engine_driver.select_activity(self.sequence)
        mock_post.assert_called_once_with(test_url, headers=self.engine.engine_driver.headers, json=expected_payload)
        self.assertEqual(result, expected_source_url)
