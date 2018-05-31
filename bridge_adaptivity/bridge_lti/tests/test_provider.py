import logging

from ddt import data, ddt
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import Client, RequestFactory
from django.urls import reverse
from lti.contrib.django import DjangoToolProvider
import mock

from bridge_lti.provider import learner_flow
from module.models import Sequence
from module.tests.test_views import BridgeTestCase

log = logging.getLogger(__name__)


@ddt
class ProviderTest(BridgeTestCase):

    @mock.patch('bridge_lti.provider.get_tool_provider_for_lti')
    @mock.patch('bridge_lti.provider.instructor_flow')
    @mock.patch('bridge_lti.provider.learner_flow')
    @data('Instructor', 'Administrator')
    def test_lti_launch_instructor_flow(
            self, role, mock_learner_flow, mock_instructor_flow, mock_get_tool_provider_for_lti
    ):
        mock_get_tool_provider_for_lti.return_value = True
        mock_instructor_flow.return_value = HttpResponse(status=200)
        mock_learner_flow.return_value = HttpResponse(status=200)
        mock_collection_id = '1'
        self.client.post(
            reverse(
                'lti:launch',
                kwargs={
                    'collection_id': mock_collection_id,
                    'group_slug': 'group-slug',
                }),
            data={
                'oauth_nonce': 'oauth_nonce',
                'oauth_consumer_key': self.lti_provider.consumer_key,
                'roles': role,
            }
        )
        mock_instructor_flow.assert_called_once_with(mock.ANY, collection_id=mock_collection_id)
        mock_learner_flow.assert_not_called()

    @mock.patch('bridge_lti.provider.get_tool_provider_for_lti')
    @mock.patch('bridge_lti.provider.instructor_flow')
    @mock.patch('bridge_lti.provider.learner_flow')
    def test_lti_launch_student_flow(self, mock_learner_flow, mock_instructor_flow, mock_get_tool_provider_for_lti):
        mock_instructor_flow.return_value = HttpResponse(status=200)
        mock_learner_flow.return_value = HttpResponse(status=200)
        mock_tool_provider = 'tool_provider'
        mock_get_tool_provider_for_lti.return_value = mock_tool_provider
        mock_collection_id = '123'
        mock_group_slug = '1234-124'
        mock_unique_marker = '434'

        Client().post(
            reverse(
                'lti:launch',
                kwargs={
                    'collection_id': mock_collection_id,
                    'group_slug': mock_group_slug,
                    'unique_marker': mock_unique_marker,
                }),
            data={
                'oauth_nonce': 'oauth_nonce',
                'oauth_consumer_key': self.lti_provider.consumer_key,
                'roles': 'Learner',
            }
        )

        mock_learner_flow.assert_called_once_with(
            mock.ANY,
            self.lti_provider,
            mock_tool_provider,
            collection_id=mock_collection_id,
            group_slug=mock_group_slug,
            unique_marker=mock_unique_marker,
        )
        mock_instructor_flow.assert_not_called()

    def test_learner_flow_different_user_creation(self):
        mock_request = RequestFactory().post(
            '',
            data={
                'oauth_nonce': 'oauth_nonce',
                'oauth_consumer_key': self.lti_provider.consumer_key,
                'roles': 'Learner',
                'user_id': 'user_id',
                'context_id': 'some+course+id'
            }
        )
        middleware = SessionMiddleware()
        middleware.process_request(mock_request)
        mock_request.session.save()

        tool_provider = DjangoToolProvider.from_django_request(request=mock_request)

        count_of_the_sequence = Sequence.objects.all().count()

        # We call 2 time for ensure that implement logic for creating sequence for second call

        learner_flow(mock_request, self.lti_provider, tool_provider, self.collection1.id, self.test_cg.slug)
        learner_flow(mock_request, self.lti_provider, tool_provider, self.collection1.id, self.test_cg.slug)
        self.assertEqual(Sequence.objects.all().count(), count_of_the_sequence + 1)

        count_of_the_sequence += 1
        learner_flow(mock_request, self.lti_provider, tool_provider, self.collection1.id, self.test_cg.slug, 'marker')
        learner_flow(mock_request, self.lti_provider, tool_provider, self.collection1.id, self.test_cg.slug, 'marker')
        self.assertEqual(Sequence.objects.all().count(), count_of_the_sequence + 1)

        count_of_the_sequence += 1
        learner_flow(mock_request, self.lti_provider, tool_provider, self.collection1.id, self.test_cg.slug, 'marker1')
        learner_flow(mock_request, self.lti_provider, tool_provider, self.collection1.id, self.test_cg.slug, 'marker2')
        self.assertEqual(Sequence.objects.all().count(), count_of_the_sequence + 2)
