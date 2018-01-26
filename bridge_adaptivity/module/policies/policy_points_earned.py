from .base import BaseGradingPolicy


class PointsEarnedGradingPolicy(BaseGradingPolicy):
    """Grading policy class calculate grade based upon users earned points."""

    public_name = 'Points earned'

    def _calculate(self):
        trials_count, points_earned = self._get_points_earned_trials_count()
        return self.internal_calculate(points_earned)
