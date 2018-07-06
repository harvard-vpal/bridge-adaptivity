from django.db.models.aggregates import Count, Sum

from .base import BaseGradingPolicy


class PointsEarnedGradingPolicy(BaseGradingPolicy):
    """Grading policy class calculate grade based upon users earned points."""

    public_name = 'Points earned'
    require = {
        'threshold': True
    }

    summary_text = """Overall score is the proportion of points earned out of either the total possible points
    earnable, or the threshold Q, whichever is higher."""

    detail_text = """Let a_i denote the points available for the i'th activity in the sequence. Let e_i denote the
    student's points earned for the i'th activity in the sequence. Let Q, the threshold (a configurable parameter) be a
    positive integer. Then the sequence score is sum(e_i)/(max(Q,sum_i(a_i)).
    The effect of Q, a "minimum available points threshold" is to encourage students to keep doing problems in the
    sequence until the sum of the available points in the sequence is greater than Q, otherwise they will not be able
    to attain full credit.
    """

    def _get_points_earned_trials_count(self):
        """Get points earned and trials count from the sequence.

        :return tuple([trials_count, points_earned])
        """
        items_result = self.sequence.items.exclude(is_problem=False).aggregate(
            points_earned=Sum('score'), trials_count=Count('score')
        )
        # Note(idegtiarov) With the default 0 threshold and first non-problem activity in the sequence item_result
        # returns None, None which are not appropriate for the grade calculation method, default values are provided to
        # fix this issue
        return (items_result['trials_count'] or 1), (items_result['points_earned'] or 0)

    def _calculate(self):
        trials_count, points_earned = self._get_points_earned_trials_count()
        return round(float(points_earned) / max(self.policy.threshold, trials_count), 4)

    @classmethod
    def get_form_class(cls):
        from module.forms import ThresholdGradingPolicyForm
        return ThresholdGradingPolicyForm

    def send_grade(self):
        """Send grade to LMS system.

        :return: nothing.
        """
        self._send_grade(with_request=True)
