from .base import BaseGradingPolicy


class TrialsCountGradingPolicy(BaseGradingPolicy):
    public_name = 'Trials count'

    def _calculate(self):
        trials_count, _ = self._get_points_earned_trials_count()
        return self._internal_calculate(trials_count)
