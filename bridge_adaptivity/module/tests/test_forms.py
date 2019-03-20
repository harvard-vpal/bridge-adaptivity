from ddt import data, ddt, unpack
from django.test import TestCase

from module.forms import ThresholdGradingPolicyForm


@ddt
class ThresholdGradingPolicyFormTest(TestCase):
    """
    Test ThresholdGradingPolicyForm for the `trials_count` and `points_earned` policies.
    """

    @data('trials_count', 'points_earned')
    def test_grading_policy_params_default_values(self, policy_name):
        payload = {
            'name': policy_name,
        }
        policy = ThresholdGradingPolicyForm(payload)
        self.assertTrue(policy.is_valid())
        # NOTE(idegtiarov) currently `threshold` is the only policy's parameter with the default value,
        # which is equal to 1
        self.assertEqual(policy.clean()['params']['threshold'], 1)

    @unpack
    @data(
        {'policy_name': 'trials_count', 'threshold': -10},
        {'policy_name': 'trials_count', 'threshold': 0},
        {'policy_name': 'trials_count', 'threshold': "not_valid"},
        {'policy_name': 'points_earned', 'threshold': -10},
        {'policy_name': 'points_earned', 'threshold': 0},
        {'policy_name': 'points_earned', 'threshold': "not_valid"},
    )
    def test_grading_policy_parameter_negative_threshold_validation(self, policy_name, threshold):
        payload = {
            'name': policy_name,
            'params': {'threshold': threshold}
        }
        policy = ThresholdGradingPolicyForm(payload)
        self.assertTrue(policy.is_valid())
        # NOTE(idegtiarov) `threshold` validation ignore not positive value (<= 0) and exchange it with the default one.
        self.assertEqual(policy.clean()['params']['threshold'], 1)
