from django.db.models.aggregates import Sum, Count
from .base import GradingPolicy


class PointsEarnedGradingPolicy(GradingPolicy):
    """GRadding policy class calculate grade based upon users earned points"""

    public_name = 'Points earned'
    internal_name = 'points_earned'

    def _calculate(self):
        trials_count, points_earned = self._get_points_earned_trials_count()
        return float(points_earned) / max(self.policy.threshold, trials_count)
