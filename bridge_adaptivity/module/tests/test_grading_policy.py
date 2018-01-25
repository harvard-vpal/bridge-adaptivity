from ddt import data, ddt, unpack
from django.test import TestCase
import mock
import pytest

from module.models import GRADING_POLICY_NAME_TO_CLS, GradingPolicy
from module.policies.policy_points_earned import PointsEarnedGradingPolicy
from module.policies.policy_trials_count import TrialsCountGradingPolicy


GRADING_POLICY_TEST_DATA = (
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 0, 'trials_count': 1, 'points_earned': 0, 'er': 0},
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 1, 'trials_count': 1, 'points_earned': 0, 'er': 0},
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 1, 'trials_count': 0, 'points_earned': 1, 'er': 1},
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 0, 'trials_count': 1, 'points_earned': 0, 'er': 0},
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 1, 'trials_count': 1, 'points_earned': 0, 'er': 0},
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 1, 'trials_count': 0, 'points_earned': 1, 'er': 1},
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 2, 'trials_count': 1, 'points_earned': 0.5,
     'er': 0.25},
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 2, 'trials_count': 5, 'points_earned': 0.7,
     'er': 0.14},
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 40, 'trials_count': 3, 'points_earned': 0.75,
     'er': 0.02},

    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 0, 'trials_count': 1, 'points_earned': 0, 'er': 1},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 1, 'trials_count': 1, 'points_earned': 0, 'er': 1},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 1, 'trials_count': 0, 'points_earned': 0, 'er': 0},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 0, 'trials_count': 1, 'points_earned': 0, 'er': 1},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 1, 'trials_count': 1, 'points_earned': 0, 'er': 1},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 1, 'trials_count': 0, 'points_earned': 0, 'er': 0},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 1, 'trials_count': 0, 'points_earned': 0, 'er': 0},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 0, 'trials_count': 3., 'points_earned': 0, 'er': 1.},


    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 4, 'trials_count': 4., 'points_earned': 0, 'er': 1.},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 5, 'trials_count': 4., 'points_earned': 0, 'er': 0.8},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 20, 'trials_count': 10., 'points_earned': 0, 'er': 0.5},

    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 4, 'trials_count': 3., 'points_earned': 0, 'er': 0.75}
)


@ddt
class TestGradingPolicyObject(TestCase):
    """Integration test for GradingPolicy modules."""

    fixtures = ['gradingpolicy.json']

    @unpack
    @data(
        {'test_cls': PointsEarnedGradingPolicy, 'public_name': 'Points earned'},
        {'test_cls': TrialsCountGradingPolicy, 'public_name': 'Trials count'}
    )
    def test_grading_policy_has_name(self, test_cls, public_name):
        """Test that GradingPolicy sub-classes has name and public name."""
        self.assertIsNotNone(getattr(test_cls, 'public_name', None))
        self.assertEqual(getattr(test_cls, 'public_name'), public_name)

    @mock.patch('module.policies.base.BaseGradingPolicy._get_points_earned_trials_count')
    @unpack
    @data(*GRADING_POLICY_TEST_DATA)
    def test_policy_math(
            self, points_earned_trials_count, GradingPolicyCls, threshold, trials_count, points_earned, er
    ):
        points_earned_trials_count.return_value = trials_count, points_earned
        POLICY_CLS_TO_NAME = {v: k for k, v in GRADING_POLICY_NAME_TO_CLS.items()}
        policy = GradingPolicy.objects.filter(name=POLICY_CLS_TO_NAME[GradingPolicyCls]).first()
        self.assertIsNotNone(policy)
        policy.threshold = threshold
        # pass sequence = None - this is a stub to not create a lot of objects in DB and test only math here
        if er and type(er) == type and issubclass(er, Exception):
            with pytest.raises(er):
                GradingPolicyCls(sequence=None, policy=policy)._calculate()
        else:
            grade = GradingPolicyCls(sequence=None, policy=policy)._calculate()
            self.assertEqual(grade, er)
            self.assertIsInstance(grade, float)
