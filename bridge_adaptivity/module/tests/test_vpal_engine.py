from django.test import TestCase
from mock import patch

from bridge_lti.models import BridgeUser, LtiProvider, LtiUser, OutcomeService
from module.models import Activity, Collection, Engine, GradingPolicy, Sequence, SequenceItem
from module.engines import engine_vpal


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
        self.a1 = Activity.objects.create(name='act1', collection=self.collection, source_launch_url='test_url_act1')
        self.lti_consumer = LtiProvider.objects.create(
            consumer_name='test_consumer_name',
            consumer_key='test_consumer_key',
            consumer_secret='test_consumer_secret',
        )
        self.lti_user = LtiUser.objects.create(
            user_id='test_ltiuser_id',
            lti_consumer=self.lti_consumer,
        )
        self.engine = Engine.objects.create(engine='engine_vpal')
        self.grading_policy = GradingPolicy.objects.create(name='trials_count', public_name='test_policy')
        self.sequence = Sequence.objects.create(
            lti_user=self.lti_user,
            collection=self.collection,
            engine=self.engine,
            grading_policy=self.grading_policy,
        )
        self.sequence_item = SequenceItem.objects.create(sequence=self.sequence, activity=self.a1, score=0.4)

    def test_fulfill_payload(self):
        payload = self.engine.engine_driver.fulfill_payload(instance_to_parse=self.sequence_item)
        raise Exception(payload)
