import mock
import pytest
from django.test import TestCase
from ddt import ddt, data, unpack

from module.models import GradingPolicy
from module.policies.policy_points_earned import PointsEarnedGradingPolicy
from module.policies.policy_trials_count import TrialsCountGradingPolicy

@ddt
class TestGradingPolicyObject(TestCase):
    """Integration tests for GradingPolicy modules"""

    fixtures = ['gradingpolicy.json']

    @unpack
    @data(
        {'test_cls': PointsEarnedGradingPolicy, 'name': 'points_earned'},
        {'test_cls': TrialsCountGradingPolicy, 'name': 'trials_count'}
    )
    def test_grading_policy_has_name(self, test_cls, name):
        """Test that GradingPolicy sub-classes has name and public name"""
        self.assertEqual(test_cls.internal_name, name)
        self.assertIsNotNone(getattr(test_cls, 'public_name', None))

    @mock.patch('module.policies.base.GradingPolicy._get_points_earned_trials_count')
    @unpack
    @data(
        {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 0, 'trials_count': 1, 'points_earned': 0, 'er': 0},
        {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 1, 'trials_count': 1, 'points_earned': 0, 'er': 0},
        {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 0, 'trials_count': 0, 'points_earned': 1, 'er': ZeroDivisionError},
        {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 1, 'trials_count': 0, 'points_earned': 1, 'er': 1},
        {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 0, 'trials_count': 1, 'points_earned': 0, 'er': 0},
        {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 1, 'trials_count': 1, 'points_earned': 0, 'er': 0},
        {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 0, 'trials_count': 0, 'points_earned': 1, 'er': ZeroDivisionError},
        {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 1, 'trials_count': 0, 'points_earned': 1, 'er': 1},
        {'GradingPolicyCls': PointsEarnedGradingPolicy, 'threshold': 4, 'trials_count': 3, 'points_earned': 0.75, 'er': 0.1875},

        {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 0, 'trials_count': 1, 'points_earned': 0, 'er': 1},
        {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 1, 'trials_count': 1, 'points_earned': 0, 'er': 1},
        {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 0, 'trials_count': 0, 'points_earned': 0, 'er': ZeroDivisionError},
        {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 1, 'trials_count': 0, 'points_earned': 0, 'er': 0},
        {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 0, 'trials_count': 1, 'points_earned': 0, 'er': 1},
        {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 1, 'trials_count': 1, 'points_earned': 0, 'er': 1},
        {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 0, 'trials_count': 0, 'points_earned': 0, 'er': ZeroDivisionError},
        {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 1, 'trials_count': 0, 'points_earned': 0, 'er': 0},
        {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 1, 'trials_count': 0, 'points_earned': 0, 'er': 0},
        {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 0, 'trials_count': 3., 'points_earned': 0, 'er': 1.},
        {'GradingPolicyCls': TrialsCountGradingPolicy, 'threshold': 4, 'trials_count': 3., 'points_earned': 0, 'er': 0.75},
    )
    def test_trials_count_math(self, points_earned_trials_count, GradingPolicyCls, threshold, trials_count, points_earned, er):
        points_earned_trials_count.return_value = trials_count, points_earned

        policy = GradingPolicy.objects.filter(name=GradingPolicyCls.internal_name).first()
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





