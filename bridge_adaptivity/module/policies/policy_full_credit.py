from bridge_lti.outcomes import update_lms_grades
from .base import BaseGradingPolicy


class FullCreditOnCompleteGradingPolicy(BaseGradingPolicy):
    """Grading policy that gives full credit only on sequence completion, so that topic mastery is encouraged."""

    public_name = "Grade on sequence completion"

    def _calculate(self):
        return float(self.sequence.completed)

    def send_grade(self, is_callback=False):
        """Send grade to LMS system.

        Call update_lms_grades(self.context['request'], sequence=self.sequence, user_id=self.context['user_id'])
        :param is_callback: is true if method called from callback_sequence_item_grade view, otherwise False
        :return: nothing.
        """
        if not is_callback:
            update_lms_grades(self.context['request'], sequence=self.sequence, user_id=self.context['user_id'])
