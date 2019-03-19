import urllib.parse

from ddt import data, ddt
from django.test import TestCase
from mock import Mock, patch

from bridge_lti.models import BridgeUser, LtiLmsPlatform, LtiUser, OutcomeService
from module.engines import engine_vpal
from module.models import (
    Activity, Collection, CollectionOrder, Engine, GradingPolicy, ModuleGroup, Sequence, SequenceItem
)


@ddt
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
            repetition=2,
        )
        self.a2 = Activity.objects.create(
            name='act2',
            collection=self.collection,
            source_launch_url='test_url_act2',
            stype='problem',
        )
        self.lti_content_source = LtiLmsPlatform.objects.create(
            consumer_name='test_consumer_name',
            consumer_key='test_consumer_key',
            consumer_secret='test_consumer_secret',
        )
        self.lti_user = LtiUser.objects.create(
            user_id='test_ltiuser_id',
            lti_lms_platform=self.lti_content_source,
        )
        self.engine = Engine.objects.create(engine='engine_vpal', lti_parameters=' lis_person_sourcedid, lis_unknown')
        self.grading_policy = GradingPolicy.objects.create(name='trials_count', public_name='test_policy')

        self.group = ModuleGroup.objects.create(name='test-group', owner=self.user)

        self.collection_order = CollectionOrder.objects.create(
            group=self.group,
            collection=self.collection,
            engine=self.engine,
            grading_policy=self.grading_policy,
        )

        self.outcome_service = OutcomeService.objects.create(
            lis_outcome_service_url='http://test.outcome_service.net',
            lms_lti_connection=self.lti_content_source,
        )

        self.sequence = Sequence.objects.create(
            lti_user=self.lti_user,
            collection_order=self.collection_order,
            outcome_service=self.outcome_service,
        )
        self.sequence_item_1 = SequenceItem.objects.create(sequence=self.sequence, activity=self.a1, score=0.4)
        self.sequence_item_2 = SequenceItem.objects.create(sequence=self.sequence, activity=self.a2, score=0.6)

    def test_fulfill_sequenceitem_payload(self):
        expected = {'activity': self.a1.source_launch_url, 'score': self.sequence_item_1.score, 'is_problem': False}
        payload = self.engine.engine_driver.fulfill_payload(instance_to_parse=self.sequence_item_1)
        self.assertEqual(payload, expected)

    def test_fulfill_activity_payload(self):
        expected = {
            'difficulty': '0.5',
            'name': 'act1',
            'repetition': 2,
            'source_launch_url': 'test_url_act1',
            'tags': None,
            'type': 'generic',
        }

        payload = self.engine.engine_driver.fulfill_payload(payload={}, instance_to_parse=self.a1)
        self.assertEqual(payload, expected)

    @data(200, 201)
    def test_select_activity(self, mock_status):
        expected_source_url = 'new_activity_source_url'
        lti_param = "lis_person_sourcedid"
        launch_params = {lti_param: "test_lis_person_sourcedid"}
        self.sequence.fulfil_sequence_metadata(self.engine.lti_params, launch_params)
        test_url = urllib.parse.urljoin(
            "{}/".format(self.engine.engine_driver.activity_url), "recommend"
        )
        expected_payload = {
            "learner": {
                'user_id': self.sequence.lti_user.user_id,
                # NOTE(idegtiarov) `tool_consumer_instance_guid` is equal to the LtiLmsPlatform.consumer_name if it is
                # not add to the Engine.lti_parameters or not found in received lti_launch parameters.
                'tool_consumer_instance_guid': self.lti_content_source.consumer_name,
            },
            "collection": self.sequence.collection_order.collection.slug,
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
        with patch('requests.post', return_value=Mock(status_code=mock_status)) as mock_post:
            response = mock_post.return_value
            response.json.return_value = {'source_launch_url': expected_source_url}
            result = self.engine.engine_driver.select_activity(self.sequence)
            mock_post.assert_called_once_with(
                test_url, headers=self.engine.engine_driver.headers, json=expected_payload
            )
            self.assertEqual(result.get('source_launch_url'), expected_source_url)

    @data(200, 201)
    def test_tool_consumer_instance_guid_added_to_select_activity_payload(self, mock_status):
        """
        Test tool_consumer_instance_guid is added to the 'learner' parameter in the recommended request.

        For this test `tool_consumer_instance_guid` param should be added to the Engine.lti_parameter and received in
        the lti_launch request.
        """
        expected_source_url = 'very_new_activity_source_url'
        expected_tool_consumer_instance_guid = "lms.edx.net"
        self.engine.lti_parameters = "tool_consumer_instance_guid, unknown_param"
        launch_params = {
            "tool_consumer_instance_guid": expected_tool_consumer_instance_guid,
        }
        self.sequence.fulfil_sequence_metadata(self.engine.lti_params, launch_params)
        test_url = urllib.parse.urljoin(
            "{}/".format(self.engine.engine_driver.activity_url), "recommend"
        )
        expected_payload = {
            "learner": {
                'user_id': self.sequence.lti_user.user_id,
                'tool_consumer_instance_guid': expected_tool_consumer_instance_guid,
            },
            "collection": self.sequence.collection_order.collection.slug,
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
        with patch('requests.post', return_value=Mock(status_code=mock_status)) as mock_post:
            response = mock_post.return_value
            response.json.return_value = {'source_launch_url': expected_source_url}
            result = self.engine.engine_driver.select_activity(self.sequence)
            mock_post.assert_called_once_with(
                test_url, headers=self.engine.engine_driver.headers, json=expected_payload
            )
            self.assertEqual(result.get('source_launch_url'), expected_source_url)

    @data(200, 201)
    def test_no_sequence_metadata_in_select_activity_payload(self, mock_status):
        """
        Test tool_consumer_instance_guid is added to the 'learner' parameter with the default consumer_name.

        `tool_consumer_instance_guid` is taken with the default value and no metadata is added to the sequence from the
        received lti parameters.
        """
        expected_source_url = 'very_new_activity_source_url'
        test_url = urllib.parse.urljoin(
            "{}/".format(self.engine.engine_driver.activity_url), "recommend"
        )
        expected_payload = {
            "learner": {
                'user_id': self.sequence.lti_user.user_id,
                'tool_consumer_instance_guid': self.lti_content_source.consumer_name,
            },
            "collection": self.sequence.collection_order.collection.slug,
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
        with patch('requests.post', return_value=Mock(status_code=mock_status)) as mock_post:
            response = mock_post.return_value
            response.json.return_value = {'source_launch_url': expected_source_url}
            result = self.engine.engine_driver.select_activity(self.sequence)
            mock_post.assert_called_once_with(
                test_url, headers=self.engine.engine_driver.headers, json=expected_payload
            )
            self.assertEqual(result.get('source_launch_url'), expected_source_url)
