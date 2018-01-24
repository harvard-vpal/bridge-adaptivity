from django.test import TestCase

from bridge_lti.models import BridgeUser, LtiProvider, LtiUser, OutcomeService
from module.models import Activity, Collection, Engine, GradingPolicy, Sequence
from module.utils import choose_activity


class TestUtilities(TestCase):
    fixtures = ['gradingpolicy', 'engine']

    def setUp(self):
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
        self.sequence = Sequence.objects.create(
            lti_user=self.lti_user,
            collection=self.collection,
            engine=self.engine,
            grading_policy=self.gading_policy,
            outcome_service=self.outcome_service
        )

    def test_choose_activity(self):
        chosen_activity = choose_activity(sequence=self.sequence)
        expected_activity = Activity.objects.get(source_launch_url=self.source_launch_url)
        self.assertEqual(chosen_activity, expected_activity)
