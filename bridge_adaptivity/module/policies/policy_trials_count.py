from .base import BaseGradingPolicy


class TrialsCountGradingPolicy(BaseGradingPolicy):
    public_name = 'Trials count'
    internal_name = 'trials_count'

    def _calculate(self):
        trials_count, _ = self._get_points_earned_trials_count()
        return float(trials_count) / max(self.policy.threshold, trials_count)
