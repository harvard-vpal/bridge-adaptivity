import logging

from django.http.response import Http404
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.urls.base import reverse
import mock
from mock import Mock
import pytest


from bridge_lti.models import BridgeUser, LtiProvider, LtiUser
from bridge_lti.provider import learner_flow
from module.models import Activity, Collection, CollectionGroup, Engine, GradingPolicy, Sequence

log = logging.getLogger(__name__)


def dont_check_lti_keys(func):
    def wrap(self, *a, **kw):
        with mock.patch('lti.contrib.django.DjangoToolProvider.from_django_request') as from_django_request:
            is_valid_request = Mock(parent=from_django_request, return_value=True)
            tool_provider = Mock(return_value=is_valid_request)
            tool_provider.is_valid_request = Mock(return_value=True)
            tool_provider.is_outcome_service = Mock(return_value=False)
            from_django_request.return_value = tool_provider
            return func(self, *a, **kw)
    return wrap


class RaisedExceptionUsesCustomTemplateTest(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.url = reverse('lti:launch', kwargs={'collection_id': 1, 'group_slug': 'asd'})

    @override_settings(DEBUG=False)
    def test_learner_flow_with_incorrect_collection_id_test(self):
        """Check that learner_flow call with incorrect collection_id raise proper exception."""
        request = self.rf.post(self.url)
        with pytest.raises(Http404):
            learner_flow(
                request,
                lti_consumer=None,
                tool_provider=None,
                collection_id=1000
            )

    @mock.patch('lti.contrib.django.DjangoToolProvider.from_django_request')
    @override_settings(DEBUG=False)
    def test_client_post_with_incorrect_collection_id_test(self, from_django_request):
        """Test that when POST request received with not correct data it will show 404 error with correct template."""
        is_valid_request = Mock(return_value=False)
        tool_provider = Mock(is_valid_request=is_valid_request)
        from_django_request.return_value = tool_provider

        response = self.client.post(self.url)
        self.assertTemplateUsed(response, '404.html')
        from_django_request.assert_called_once()
        tool_provider.is_valid_request.assert_called_once()


class CollectionGroupGradingPolicyTest(TestCase):
    fixtures = ['gradingpolicy']

    def setUp(self):
        self.rf = RequestFactory()

        self.user = BridgeUser.objects.create_user(
            username='test',
            password='test',
            email='test@me.com'
        )

        self.lti_consumer = LtiProvider.objects.create(
            consumer_name='test',
            consumer_key='test',
            consumer_secret='test'
        )
        self.lti_user = LtiUser.objects.create(
            user_id='some_user_id',
            lti_consumer=self.lti_consumer,
            bridge_user=self.user,
            # defaults={'course_id': 'some_context'}
        )

        self.client.login(username='test', password='test')

        self.setup_collections_groups_policies()

        Activity.objects.create(
            name='start',
            collection=self.collection1,
            atype='G'
        )

    def setup_collections_groups_policies(self):
        self.collection1 = Collection.objects.create(name='col1', owner=self.user)
        self.collection2 = Collection.objects.create(name='col2', owner=self.user)
        self.collection3 = Collection.objects.create(name='col3', owner=self.user)
        self.collection4 = Collection.objects.create(name='col4', owner=self.user)

        self.engine = Engine.objects.create(name='mock')

        self.test_cg_trials = CollectionGroup.objects.create(
            name='TestColGroup 0',
            owner=self.user,
            engine=self.engine,
        )
        self.test_cg_trials.collections.add(self.collection1)
        self.test_cg_trials.collections.add(self.collection3)

        self.test_cg_points = CollectionGroup.objects.create(
            name='TestColGroup 1',
            owner=self.user,
            engine=self.engine
        )
        self.test_cg_points.collections.add(self.collection2)
        self.test_cg_points.collections.add(self.collection4)

        self.grading_policy_points = GradingPolicy.objects.get(name='points_earned')
        self.test_cg_points.grading_policy = self.grading_policy_points
        self.test_cg_points.save()

        self.grading_policy_trials = GradingPolicy.objects.get(name='trials_count')
        self.test_cg_trials.grading_policy = self.grading_policy_trials
        self.test_cg_trials.save()

    @dont_check_lti_keys
    # @mock.patch('module.utils.choose_activity', return_value=True)
    def test_sequence_has_collection_group_after_launch(self):
        """Test sequence has collection_group attr and it is not None."""
        response = self.client.post(
            reverse(
                'lti:launch',
                kwargs={'collection_id': self.collection1.id, 'group_slug': self.test_cg_trials.slug}
            ),
            data={
                'user_id': 'some_user_id',
                'context_id': 'some_context',
                'oauth_nonce': 'fsdf',
                'oauth_consumer_key': 'test'
            }
        )

        sequence = Sequence.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(sequence.collection_group, self.test_cg_trials)
        self.assertEqual(sequence.grading_policy, self.grading_policy_trials)
