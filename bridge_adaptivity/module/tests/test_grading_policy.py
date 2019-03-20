from ddt import data, ddt, unpack
from django.test import TestCase
from django.test.client import RequestFactory
import mock
import pytest

from bridge_lti.models import LtiLmsPlatform, OutcomeService
from module.models import (
    Activity, BridgeUser, Collection, CollectionOrder, Engine, GRADING_POLICY_NAME_TO_CLS, GradingPolicy, LtiUser,
    ModuleGroup, Sequence, SequenceItem
)
from module.policies.policy_full_credit import FullCreditOnCompleteGradingPolicy
from module.policies.policy_points_earned import PointsEarnedGradingPolicy
from module.policies.policy_trials_count import TrialsCountGradingPolicy

GRADING_POLICY_TEST_DATA = (
    {
        'GradingPolicyCls': PointsEarnedGradingPolicy,
        'params': {'threshold': 0},
        'trials_count': 1,
        'points_earned': 0,
        'sequence': Sequence(),
        'er': 0
    },
    {
        'GradingPolicyCls': PointsEarnedGradingPolicy,
        'params': {'threshold': 1},
        'trials_count': 1,
        'points_earned': 0,
        'sequence': Sequence(),
        'er': 0
    },
    {
        'GradingPolicyCls': PointsEarnedGradingPolicy,
        'params': {'threshold': 1},
        'trials_count': 0,
        'points_earned': 1,
        'sequence': Sequence(),
        'er': 1
    },
    {
        'GradingPolicyCls': PointsEarnedGradingPolicy,
        'params': {'threshold': 0},
        'trials_count': 1,
        'points_earned': 0,
        'sequence': Sequence(),
        'er': 0
    },
    {
        'GradingPolicyCls': PointsEarnedGradingPolicy,
        'params': {'threshold': 1},
        'trials_count': 1,
        'points_earned': 0,
        'sequence': Sequence(),
        'er': 0
    },
    {
        'GradingPolicyCls': PointsEarnedGradingPolicy,
        'params': {'threshold': 1},
        'trials_count': 0,
        'points_earned': 1,
        'sequence': Sequence(),
        'er': 1
    },
    {
        'GradingPolicyCls': PointsEarnedGradingPolicy,
        'params': {'threshold': 2},
        'trials_count': 1,
        'points_earned': 0.5,
        'sequence': Sequence(),
        'er': 0.25
    },
    {
        'GradingPolicyCls': PointsEarnedGradingPolicy,
        'params': {'threshold': 2},
        'trials_count': 5,
        'points_earned': 0.7,
        'sequence': Sequence(),
        'er': 0.14
    },
    {
        'GradingPolicyCls': PointsEarnedGradingPolicy,
        'params': {'threshold': 40},
        'trials_count': 3,
        'points_earned': 0.75,
        'sequence': Sequence(),
        'er': 0.0187
    },
    {
        'GradingPolicyCls': TrialsCountGradingPolicy,
        'params': {'threshold': 0},
        'trials_count': 1,
        'points_earned': 0,
        'sequence': Sequence(),
        'er': 1
    },
    {
        'GradingPolicyCls': TrialsCountGradingPolicy,
        'params': {'threshold': 1},
        'trials_count': 1,
        'points_earned': 0,
        'sequence': Sequence(),
        'er': 1
    },
    {
        'GradingPolicyCls': TrialsCountGradingPolicy,
        'params': {'threshold': 1},
        'trials_count': 0,
        'points_earned': 0,
        'sequence': Sequence(),
        'er': 0
    },
    {
        'GradingPolicyCls': TrialsCountGradingPolicy,
        'params': {'threshold': 0},
        'trials_count': 1,
        'points_earned': 0,
        'sequence': Sequence(),
        'er': 1
    },
    {
        'GradingPolicyCls': TrialsCountGradingPolicy,
        'params': {'threshold': 1},
        'trials_count': 1,
        'points_earned': 0,
        'sequence': Sequence(),
        'er': 1
    },
    {
        'GradingPolicyCls': TrialsCountGradingPolicy,
        'params': {'threshold': 1},
        'trials_count': 0,
        'points_earned': 0,
        'sequence': Sequence(),
        'er': 0
    },
    {
        'GradingPolicyCls': TrialsCountGradingPolicy,
        'params': {'threshold': 1},
        'trials_count': 0,
        'points_earned': 0,
        'sequence': Sequence(),
        'er': 0
    },
    {
        'GradingPolicyCls': TrialsCountGradingPolicy,
        'params': {'threshold': 0},
        'trials_count': 3.,
        'points_earned': 0,
        'sequence': Sequence(),
        'er': 1.
    },
    {
        'GradingPolicyCls': TrialsCountGradingPolicy,
        'params': {'threshold': 4},
        'trials_count': 4.,
        'points_earned': 0,
        'sequence': Sequence(),
        'er': 1.
    },
    {
        'GradingPolicyCls': TrialsCountGradingPolicy,
        'params': {'threshold': 5},
        'trials_count': 4.,
        'points_earned': 0,
        'sequence': Sequence(),
        'er': 0.8
    },
    {
        'GradingPolicyCls': TrialsCountGradingPolicy,
        'params': {'threshold': 20},
        'trials_count': 10.,
        'points_earned': 0,
        'sequence': Sequence(),
        'er': 0.5
    },
    {
        'GradingPolicyCls': TrialsCountGradingPolicy,
        'params': {'threshold': 4},
        'trials_count': 3.,
        'points_earned': 0,
        'sequence': Sequence(),
        'er': 0.75
    },
    {
        'GradingPolicyCls': FullCreditOnCompleteGradingPolicy,
        'params': {'threshold': 4},
        'trials_count': 3.,
        'points_earned': 0,
        'sequence': Sequence(completed=False),
        'er': 0
    },
    {
        'GradingPolicyCls': FullCreditOnCompleteGradingPolicy,
        'params': {'threshold': 4},
        'trials_count': 3.,
        'points_earned': 0,
        'sequence': Sequence(completed=True),
        'er': 1
    },
)


@ddt
class TestGradingPolicyObject(TestCase):
    """Integration test for GradingPolicy modules."""

    fixtures = ['gradingpolicy.json']

    @unpack
    @data(
        {'test_cls': PointsEarnedGradingPolicy, 'public_name': 'Points earned'},
        {'test_cls': TrialsCountGradingPolicy, 'public_name': 'Trials count'},
        {'test_cls': FullCreditOnCompleteGradingPolicy, 'public_name': 'Grade on sequence completion'},
    )
    def test_grading_policy_has_name(self, test_cls, public_name):
        """Test that GradingPolicy sub-classes has name and public name."""
        self.assertIsNotNone(getattr(test_cls, 'public_name', None))
        self.assertEqual(getattr(test_cls, 'public_name'), public_name)

    @unpack
    @data(*GRADING_POLICY_TEST_DATA)
    @mock.patch('module.policies.base.BaseGradingPolicy._get_points_earned_trials_count')
    @mock.patch('module.policies.policy_points_earned.PointsEarnedGradingPolicy._get_points_earned_trials_count')
    def test_policy_math(
        self, mock_points_earned_trials_count, mock_points_earned_get_points_earned_trials_count, GradingPolicyCls,
        params, trials_count, points_earned, sequence, er
    ):
        mock_points_earned_get_points_earned_trials_count.return_value = trials_count, points_earned
        mock_points_earned_trials_count.return_value = trials_count, points_earned

        POLICY_CLS_TO_NAME = {v: k for k, v in GRADING_POLICY_NAME_TO_CLS.items()}

        policy = GradingPolicy.objects.filter(name=POLICY_CLS_TO_NAME[GradingPolicyCls]).first()
        self.assertIsNotNone(policy)
        policy.params = params
        # pass sequence = None - this is a stub to not create a lot of objects in DB and test only math here
        if er and type(er) == type and issubclass(er, Exception):
            with pytest.raises(er):
                GradingPolicyCls(sequence=sequence, policy=policy)._calculate()
        else:
            grade = GradingPolicyCls(sequence=sequence, policy=policy)._calculate()
            self.assertEqual(grade, er)
            self.assertIsInstance(grade, (float, int))


class TestPolicySendGradeMethod(TestCase):
    fixtures = ['gradingpolicy.json', 'engine.json']

    @mock.patch('module.tasks.sync_collection_engines.apply_async')
    def setUp(self, mock_apply_async):
        self.rf = RequestFactory()
        self.user = BridgeUser.objects.create_user(
            username='test_user',
            password='test_pass',
            email='test@test.com'
        )
        self.collection = Collection.objects.create(name='testcol1', owner=self.user)
        self.collection2 = Collection.objects.create(name='testcol2', owner=self.user)

        self.source_launch_url = 'http://test_source_launch_url.com'
        self.activity = Activity.objects.create(
            name='testactivity1', collection=self.collection, source_launch_url=self.source_launch_url
        )
        self.activity2 = Activity.objects.create(
            name='testactivity2', collection=self.collection2, source_launch_url=self.source_launch_url, stype='problem'
        )
        self.lti_lms_platform = LtiLmsPlatform.objects.create(
            consumer_name='test_consumer', consumer_key='test_consumer_key', consumer_secret='test_consumer_secret'
        )
        self.lti_user = LtiUser.objects.create(
            user_id='test_user_id', lti_lms_platform=self.lti_lms_platform, bridge_user=self.user
        )
        self.engine = Engine.objects.get(engine='engine_mock')
        self.grading_policy = GradingPolicy.objects.get(name='trials_count')
        self.outcome_service = OutcomeService.objects.create(
            lis_outcome_service_url='test_url', lms_lti_connection=self.lti_lms_platform
        )

        self.test_cg = ModuleGroup.objects.create(
            name='TestColGroup',
            owner=self.user,
        )

        self.collection_order = CollectionOrder.objects.create(
            group=self.test_cg,
            collection=self.collection,
            engine=self.engine,
            grading_policy=self.grading_policy
        )

        self.sequence = Sequence.objects.create(
            lti_user=self.lti_user,
            collection_order=self.collection_order,
            outcome_service=self.outcome_service
        )

    @mock.patch('module.policies.base.update_lms_grades')
    def test_send_grade_method_policy_points_earned(self, mock_update_lms_grades):
        """Test policy.send_grade method for policy PointsEarned."""
        request = self.rf.get('/')
        policy_model = GradingPolicy.objects.get(name='points_earned')
        policy = policy_model.policy_instance(
            sequence=self.sequence,
            request=request,
            user_id=self.lti_user.user_id
        )
        default_kw = {
            'sequence': self.sequence,
        }
        policy.send_grade()
        mock_update_lms_grades.assert_called_with(*(request,), **default_kw)

    @mock.patch('module.policies.base.update_lms_grades')
    def test_send_grade_method_policies_trials_count_full_credit(self, mock_update_lms_grades):
        """Test policy.send_grade method for policies TrialsCount and FullCreditOnComplete."""
        for policy_model in GradingPolicy.objects.filter(name__in=['trials_count', 'full_credit']):
            policy = policy_model.policy_instance(
                sequence=self.sequence,
                user_id=self.lti_user.user_id
            )
            default_kw = {
                'sequence': self.sequence,
            }
            policy.send_grade()
            mock_update_lms_grades.assert_called_with(**default_kw)


class TestPolicyCalculateMethod(TestPolicySendGradeMethod):

    def setUp(self):
        super().setUp()
        self.sequence_item = SequenceItem.objects.create(
            sequence=self.sequence, activity=self.activity, is_problem=False
        )

    def test_points_earned_calculation_one_non_problem_activity(self):
        """
        Test issue when the non-problem activity appear to be the first at the sequence.

        Additional case is tested when points_earned policy with the threshold set with default value 0, value is set in
        the fixture.
        """
        policy_model = GradingPolicy.objects.get(name='points_earned')
        policy = policy_model.policy_instance(sequence=self.sequence)
        grade = policy._calculate()
        self.assertEqual(0, grade)

    def test_points_earned_calculation_two_activities(self):
        """
        Test issue when the non-problem activity appear to be the first at the sequence.

        Additional case is tested when points_earned policy with the threshold set with default value 0, value is set in
        the fixture.
        """
        policy_model = GradingPolicy.objects.get(name='points_earned')
        policy = policy_model.policy_instance(sequence=self.sequence)
        SequenceItem.objects.create(sequence=self.sequence, activity=self.activity2, position=2, score=1)
        grade = policy._calculate()
        self.assertEqual(1, grade)
        SequenceItem.objects.create(sequence=self.sequence, activity=self.activity2, position=3, score=0)
        grade = policy._calculate()
        self.assertEqual(.5, grade)
