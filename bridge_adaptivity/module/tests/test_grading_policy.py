from ddt import data, ddt, unpack
from django.test import TestCase
import mock
import pytest

from module.models import GRADING_POLICY_NAME_TO_CLS, GradingPolicy, Sequence
from module.policies.policy_full_credit import FullCreditOnCompleteGradingPolicy
from module.policies.policy_points_earned import PointsEarnedGradingPolicy
from module.policies.policy_trials_count import TrialsCountGradingPolicy


GRADING_POLICY_TEST_DATA = (
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 0, 'trials_count': 1, 'points_earned': 0,
     'sequence': Sequence(), 'er': 0},
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 1, 'trials_count': 1, 'points_earned': 0,
     'sequence': Sequence(), 'er': 0},
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 1, 'trials_count': 0, 'points_earned': 1,
     'sequence': Sequence(), 'er': 1},
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 0, 'trials_count': 1, 'points_earned': 0,
     'sequence': Sequence(), 'er': 0},
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 1, 'trials_count': 1, 'points_earned': 0,
     'sequence': Sequence(), 'er': 0},
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 1, 'trials_count': 0, 'points_earned': 1,
     'sequence': Sequence(), 'er': 1},
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 2, 'trials_count': 1, 'points_earned': 0.5,
     'sequence': Sequence(), 'er': 0.25},
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 2, 'trials_count': 5, 'points_earned': 0.7,
     'sequence': Sequence(), 'er': 0.14},
    {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 40, 'trials_count': 3, 'points_earned': 0.75,
     'sequence': Sequence(), 'er': 0.0187},

    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 0, 'trials_count': 1, 'points_earned': 0,
     'sequence': Sequence(), 'er': 1},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 1, 'trials_count': 1, 'points_earned': 0,
     'sequence': Sequence(), 'er': 1},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 1, 'trials_count': 0, 'points_earned': 0,
     'sequence': Sequence(), 'er': 0},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 0, 'trials_count': 1, 'points_earned': 0,
     'sequence': Sequence(), 'er': 1},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 1, 'trials_count': 1, 'points_earned': 0,
     'sequence': Sequence(), 'er': 1},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 1, 'trials_count': 0, 'points_earned': 0,
     'sequence': Sequence(), 'er': 0},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 1, 'trials_count': 0, 'points_earned': 0,
     'sequence': Sequence(), 'er': 0},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 0, 'trials_count': 3., 'points_earned': 0,
     'sequence': Sequence(), 'er': 1.},


    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 4, 'trials_count': 4., 'points_earned': 0,
     'sequence': Sequence(), 'er': 1.},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 5, 'trials_count': 4., 'points_earned': 0,
     'sequence': Sequence(), 'er': 0.8},
    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 20, 'trials_count': 10., 'points_earned': 0,
     'sequence': Sequence(), 'er': 0.5},

    {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 4, 'trials_count': 3., 'points_earned': 0,
     'sequence': Sequence(), 'er': 0.75},

    {'GradingPolicyCls': FullCreditOnCompleteGradingPolicy, 'threshold': 4, 'trials_count': 3., 'points_earned': 0,
     'sequence': Sequence(completed=False), 'er': 0},
    {'GradingPolicyCls': FullCreditOnCompleteGradingPolicy, 'threshold': 4, 'trials_count': 3., 'points_earned': 0,
     'sequence': Sequence(completed=True), 'er': 1},
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
            threshold, trials_count, points_earned, sequence, er
    ):
        mock_points_earned_get_points_earned_trials_count.return_value = trials_count, points_earned
        mock_points_earned_trials_count.return_value = trials_count, points_earned

        POLICY_CLS_TO_NAME = {v: k for k, v in GRADING_POLICY_NAME_TO_CLS.items()}

        policy = GradingPolicy.objects.filter(name=POLICY_CLS_TO_NAME[GradingPolicyCls]).first()
        self.assertIsNotNone(policy)
        policy.threshold = threshold
        # pass sequence = None - this is a stub to not create a lot of objects in DB and test only math here
        if er and type(er) == type and issubclass(er, Exception):
            with pytest.raises(er):
                GradingPolicyCls(sequence=sequence, policy=policy)._calculate()
        else:
            grade = GradingPolicyCls(sequence=sequence, policy=policy)._calculate()
            self.assertEqual(grade, er)
            self.assertIsInstance(grade, (float, int))
