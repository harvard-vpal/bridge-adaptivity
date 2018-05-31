import logging

import mock
from ddt import data, ddt

from bridge_lti.provider import learner_flow, lti_launch
from module.models import Sequence
from module.tests.test_views import BridgeTestCase

log = logging.getLogger(__name__)


@ddt
class ProviderTest(BridgeTestCase):
    def lti_launch_request_for_role(self, roles):
        return type('', (object,), {
            'POST': {
                'oauth_nonce': 'oauth_nonce',
                'oauth_consumer_key': self.lti_provider.consumer_key,
                'roles': roles
            },
            'session': {
            }
        })()

    @mock.patch('bridge_lti.provider.get_tool_provider_for_lti')
    @mock.patch('bridge_lti.provider.instructor_flow')
    @mock.patch('bridge_lti.provider.learner_flow')
    @data('Instructor', 'Administrator')
    def test_lti_launch_instructor_flow(
            self, role, mock_learner_flow, mock_instructor_flow, mock_get_tool_provider_for_lti
    ):
        mock_get_tool_provider_for_lti.return_value = True
        mock_request = self.lti_launch_request_for_role(role)
        mock_collection_id = 'collection_id'

        lti_launch(mock_request, mock_collection_id)

        mock_instructor_flow.assert_called_once_with(mock_request, collection_id=mock_collection_id)
        mock_learner_flow.assert_not_called()

    @mock.patch('bridge_lti.provider.get_tool_provider_for_lti')
    @mock.patch('bridge_lti.provider.instructor_flow')
    @mock.patch('bridge_lti.provider.learner_flow')
    def test_lti_launch_student_flow(self, mock_learner_flow, mock_instructor_flow, mock_get_tool_provider_for_lti):
        mock_tool_provider = 'tool_provider'
        mock_get_tool_provider_for_lti.return_value = mock_tool_provider
        mock_request = self.lti_launch_request_for_role('Learner')
        mock_collection_id = 'collection_id'
        mock_group_slug = 'group_slug'
        mock_unique_marker = 'unique_marker'

        lti_launch(mock_request, mock_collection_id, group_slug=mock_group_slug, unique_marker=mock_unique_marker)

        mock_learner_flow.assert_called_once_with(
            mock_request,
            self.lti_provider,
            mock_tool_provider,
            collection_id=mock_collection_id,
            group_slug=mock_group_slug,
            unique_marker=mock_unique_marker,
        )
        mock_instructor_flow.assert_not_called()

    def test_learner_flow_different_user_creation(self):
        mock_request = type('', (object,), {
            'POST': {
                'oauth_nonce': 'oauth_nonce',
                'oauth_consumer_key': self.lti_provider.consumer_key,
                'roles': 'Learner',
                'user_id': 'user_id',
                'context_id': 'some+course+id'
            },
            'session': {
            },
        })()
        tool_provider = type('', (object,), {
            'is_outcome_service': lambda: True,
            'launch_params': {
                'lis_outcome_service_url': 'lis_outcome_service_url',
                'lis_result_sourcedid': 'lis_result_sourcedid',
            }
        })()

        count_of_the_sequance = Sequence.objects.all().count()

        learner_flow(mock_request, self.lti_provider, tool_provider, self.collection1.id, self.test_cg.slug)
        learner_flow(mock_request, self.lti_provider, tool_provider, self.collection1.id, self.test_cg.slug)
        self.assertEqual(Sequence.objects.all().count(), count_of_the_sequance + 1)

        count_of_the_sequance += 1
        learner_flow(mock_request, self.lti_provider, tool_provider, self.collection1.id, self.test_cg.slug, 'marker')
        learner_flow(mock_request, self.lti_provider, tool_provider, self.collection1.id, self.test_cg.slug, 'marker')
        self.assertEqual(Sequence.objects.all().count(), count_of_the_sequance + 1)

        count_of_the_sequance += 1
        learner_flow(mock_request, self.lti_provider, tool_provider, self.collection1.id, self.test_cg.slug, 'marker1')
        learner_flow(mock_request, self.lti_provider, tool_provider, self.collection1.id, self.test_cg.slug, 'marker2')
        self.assertEqual(Sequence.objects.all().count(), count_of_the_sequance + 2)
