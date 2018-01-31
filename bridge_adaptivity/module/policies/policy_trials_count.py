from .base import BaseGradingPolicy


class TrialsCountGradingPolicy(BaseGradingPolicy):
    public_name = 'Trials count'

    def _calculate(self):
        trials_count, _ = self._get_points_earned_trials_count()
        return round(float(trials_count) / max(self.policy.threshold, trials_count), 4)

    @classmethod
    def get_form_class(cls):
        from module.forms import ThresholdGradingPolicyForm
        return ThresholdGradingPolicyForm
