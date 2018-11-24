from .base import BaseGradingPolicy


class TrialsCountGradingPolicy(BaseGradingPolicy):
    public_name = 'Trials count'
    require = {
        'params': {'threshold': 1},
    }

    summary_text = """ Overall score is the number of attempts made divided by the threshold Q, or 1 if the number of
    attempts made is greater than Q."""

    detail_text = """Let t_i denote the student's count of attempts for the i'th activity in the sequence.
    Let Q, the threshold (a configurable parameter) be a positive integer.
    Then the sequence score is sum(t_i)/(max(Q, sum_i(t_i)).
    The effect of Q, a "minimum attempts threshold" is to encourage students to keep doing problems in the
    sequence until the sum of the attempts made in the sequence is greater than Q, otherwise they will not be able
    to attain full credit.
    """

    def _calculate(self):
        trials_count, _ = self._get_points_earned_trials_count()
        return round(float(trials_count) / max(self.policy.params["threshold"], trials_count), 4)

    @classmethod
    def get_form_class(cls):
        from module.forms import ThresholdGradingPolicyForm
        return ThresholdGradingPolicyForm
