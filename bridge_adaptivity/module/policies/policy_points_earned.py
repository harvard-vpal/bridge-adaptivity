from django.db.models.aggregates import Count, Sum

from bridge_lti.outcomes import update_lms_grades
from .base import BaseGradingPolicy


class PointsEarnedGradingPolicy(BaseGradingPolicy):
    """Grading policy class calculate grade based upon users earned points."""

    public_name = 'Points earned'

    def _get_points_earned_trials_count(self):
        """Get points earned and trials count from the sequence.

        :return tuple([trials_count, points_earned])
        """
        items_result = self.sequence.items.exclude(is_problem=False).aggregate(
            points_earned=Sum('score'), trials_count=Count('score')
        )
        return items_result['trials_count'], items_result['points_earned']

    def _calculate(self):
        trials_count, points_earned = self._get_points_earned_trials_count()
        return round(float(points_earned) / max(self.policy.threshold, trials_count), 4)

    @classmethod
    def get_form_class(cls):
        from module.forms import ThresholdGradingPolicyForm
        return ThresholdGradingPolicyForm

    def send_grade(self):
        """Send grade to LMS system.

        Call update_lms_grades(self.context['request'], sequence=self.sequence, user_id=self.context['user_id'])
        :return: nothing.
        """
        if self.context.get('request'):
            update_lms_grades(self.context.get('request'), sequence=self.sequence, user_id=self.context['user_id'])
