"""
Test correct working LTI provider.
"""
import logging

from ddt import data, ddt
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import override_settings, RequestFactory
from django.test.client import Client
from django.urls import reverse
from lti import ToolConsumer
from lti.contrib.django import DjangoToolProvider
import mock

from bridge_lti.models import BridgeUser, LtiUser
from bridge_lti.provider import learner_flow
from module.models import Sequence
from module.tests.test_views import BridgeTestCase

log = logging.getLogger(__name__)


@ddt
class ProviderTest(BridgeTestCase):
    """
    Class for testing correctly working LTI provider.
    """

    @mock.patch('bridge_lti.provider.get_tool_provider_for_lti')
    @mock.patch('bridge_lti.provider.instructor_flow')
    @mock.patch('bridge_lti.provider.learner_flow')
    @data('Instructor', 'Administrator')
    def test_lti_launch_instructor_flow(
        self, role, mock_learner_flow, mock_instructor_flow, mock_get_tool_provider_for_lti
    ):
        """
        Test instructor flow.
        """
        mock_get_tool_provider_for_lti.return_value = True
        mock_instructor_flow.return_value = HttpResponse(status=200)
        mock_learner_flow.return_value = HttpResponse(status=200)
        mock_collection_order_slug = '1'
        self.client.post(
            reverse(
                'lti:launch',
                kwargs={
                    'collection_order_slug': mock_collection_order_slug,
                }),
            data={
                'oauth_nonce': 'oauth_nonce',
                'oauth_consumer_key': self.lti_lms_platform.consumer_key,
                'roles': role,
            }
        )
        mock_instructor_flow.assert_called_once_with(mock.ANY, collection_order_slug=mock_collection_order_slug)
        mock_learner_flow.assert_not_called()

    @mock.patch('bridge_lti.provider.get_tool_provider_for_lti')
    @mock.patch('bridge_lti.provider.instructor_flow')
    @mock.patch('bridge_lti.provider.learner_flow')
    def test_lti_launch_student_flow(self, mock_learner_flow, mock_instructor_flow, mock_get_tool_provider_for_lti):
        """
        Test learner flow.
        """
        mock_instructor_flow.return_value = HttpResponse(status=200)
        mock_learner_flow.return_value = HttpResponse(status=200)
        mock_tool_provider = 'tool_provider'
        mock_get_tool_provider_for_lti.return_value = mock_tool_provider
        mock_collection_order_slug = '123'
        mock_unique_marker = '434'

        self.client.post(
            reverse(
                'lti:launch',
                kwargs={
                    'collection_order_slug': mock_collection_order_slug,
                    'unique_marker': mock_unique_marker,
                }),
            data={
                'oauth_nonce': 'oauth_nonce',
                'oauth_consumer_key': self.lti_lms_platform.consumer_key,
                'roles': 'Learner',
            }
        )

        mock_learner_flow.assert_called_once_with(
            mock.ANY,
            self.lti_lms_platform,
            mock_tool_provider,
            collection_order_slug=mock_collection_order_slug,
            unique_marker=mock_unique_marker,
        )
        mock_instructor_flow.assert_not_called()

    def test_learner_flow_different_user_creation(self):
        """
        Test different user creation.
        """
        mock_request = RequestFactory().post(
            '',
            data={
                'oauth_nonce': 'oauth_nonce',
                'oauth_consumer_key': self.lti_lms_platform.consumer_key,
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
        count_of_lti_users = LtiUser.objects.all().count()

        # learner_flow is called 2 times (here and below) to ensure that implement logic works correctly

        learner_flow(
            mock_request,
            self.lti_lms_platform,
            tool_provider,
            self.collection_order1.slug,
        )
        learner_flow(
            mock_request,
            self.lti_lms_platform,
            tool_provider,
            self.collection_order1.slug,
        )
        self.assertEqual(Sequence.objects.all().count(), count_of_the_sequence + 1)

        count_of_the_sequence += 1

        learner_flow(
            mock_request,
            self.lti_lms_platform,
            tool_provider,
            self.collection_order1.slug,
            'marker',
        )
        learner_flow(
            mock_request,
            self.lti_lms_platform,
            tool_provider,
            self.collection_order1.slug,
            'marker',
        )
        self.assertEqual(Sequence.objects.all().count(), count_of_the_sequence + 1)

        count_of_the_sequence += 1
        learner_flow(
            mock_request,
            self.lti_lms_platform,
            tool_provider,
            self.collection_order1.slug,
            'marker1',
        )
        learner_flow(
            mock_request,
            self.lti_lms_platform,
            tool_provider,
            self.collection_order1.slug,
            'marker2',
        )
        self.assertEqual(Sequence.objects.all().count(), count_of_the_sequence + 2)

        # Ensure that only one LTI user was created.
        self.assertEqual(LtiUser.objects.all().count(), count_of_lti_users + 1)

    @mock.patch('bridge_lti.provider.learner_flow')
    @data('Instructor', 'Administrator', 'Learner', 'Student')
    def test_lti_launch_correct_query(self, role, mock_learner_flow):
        """
        Test for checking LTI query.

        :param role: String identifier for role in platform
        :param mock_learner_flow: mocking method of bridge_lti.provider.learner_flow
        :param mock_instructor_flow: mocking method of bridge_lti.provider.instructor_flow
        """
        mock_learner_flow.return_value = HttpResponse(status=200)
        consumer_prams = {
            'consumer_key': self.lti_lms_platform.consumer_key,
            'consumer_secret': self.lti_lms_platform.consumer_secret,
            'launch_url': f"http://{settings.BRIDGE_HOST}" + reverse(
                'lti:launch', kwargs={
                    'collection_order_slug': self.collection_order1.slug,
                }
            ),
            'params': {
                # Required parameters
                'lti_message_type': 'basic-lti-launch-request',
                'lti_version': 'LTI-1p0',
                # The random value is used for the test purpose
                'resource_link_id': '-523523423423423423423423423',
                # Recommended parameters
                'user_id': 'bridge_user',
                'roles': role,
                'oauth_callback': 'about:blank',
                'context_id': 'bridge_collection',
            },
        }
        # Check read-only user do not exists
        read_only_user = BridgeUser.objects.filter(username='read_only')
        self.assertFalse(read_only_user)

        consumer = ToolConsumer(**consumer_prams)
        response = self.client.post(
            consumer.launch_url,
            HTTP_HOST=settings.BRIDGE_HOST,
            data=consumer.generate_launch_data(),
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        if role in ['Instructor', 'Administrator']:
            read_only_user = BridgeUser.objects.filter(username='read_only')
            self.assertTrue(read_only_user)
            self.assertEqual(response.status_code, 302)
        else:
            self.assertEqual(response.status_code, 200)

    @data('Lax', None)
    def test_lti_launch_csrf_token(self, csrf_cookie_samsite):
        """
        Test for checking csrf token in post request.

        :param csrf_cookie_samsite: value for CSRF_COOKIE_SAMESITE variable
        """
        with override_settings(CSRF_COOKIE_SAMESITE=csrf_cookie_samsite):
            csrf_client = Client(enforce_csrf_checks=True)
            csrf_cookie_expected_result = csrf_cookie_samsite or ''
            # Get csrf_token
            response_get = csrf_client.get(reverse('login'))
            cookies_item = {}
            for key, value in response_get.cookies.items():
                cookies_item[key] = value
            csrftoken = cookies_item['csrftoken']
            csrftoken_id, samesite = csrftoken.coded_value, csrftoken.get('samesite')
            self.assertEqual(samesite, csrf_cookie_expected_result)

            response_status = 200
            if samesite:
                csrf_client.cookies.clear()
                response_status = 403
            response = csrf_client.post(
                reverse('login'),
                data={
                    'username': self.user.username,
                    'password': self.user.password,
                    'csrfmiddlewaretoken': csrftoken_id,
                }
            )
            self.assertEqual(response.status_code, response_status)

    @mock.patch('bridge_lti.provider.get_tool_provider_for_lti')
    @mock.patch('bridge_lti.provider.learner_flow')
    @mock.patch('module.views.SequenceComplete.get_object')
    @data('Lax', None)
    def test_lti_launch_session_check(
        self, session_cookie_samsite, mock_module_get_object, mock_learner_flow, mock_get_tool_provider_for_lti
    ):
        """
        Test for checking session variables in request.

        Session's variables need to be in each query.
        :param session_cookie_samsite: value for SESSION_COOKIE_SAMESITE variable
        :param mock_module_get_object: mocking method of module.views.Sequence Complete.get_object
        :param mock_learner_flow: mocking method of bridge_lti.provider.learner_flow
        :param mock_get_tool_provider_for_lti: mocking method of bridge_lti.provider.get_tool_provider_for_lti
        """
        mock_get_tool_provider_for_lti.return_value = True
        mock_learner_flow.return_value = HttpResponse(status=200)
        mock_module_get_object.__name__ = 'get_object'
        with override_settings(SESSION_COOKIE_SAMESITE=session_cookie_samsite):
            # Get session variables
            self.client.post(
                reverse(
                    'lti:launch',
                    kwargs={
                        'collection_order_slug': self.collection_order1.slug,
                    }
                ),
                data={'oauth_nonce': 'oauth_nonce', 'oauth_consumer_key': self.lti_lms_platform.consumer_key}
            )
            response_status = 200
            if session_cookie_samsite:
                # delete session. It's the same if we send get query without sessionid.
                self.client.session.flush()
                response_status = 403
            response = self.client.get(reverse('module:sequence-complete', kwargs={'pk': self.collection1.pk}))
            self.assertEqual(response.status_code, response_status)
