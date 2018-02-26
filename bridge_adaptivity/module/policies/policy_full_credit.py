from .base import BaseGradingPolicy


class FullCreditOnCompleteGradingPolicy(BaseGradingPolicy):
    """Grading policy that gives full credit only on sequence completion, so that topic mastery is encouraged."""

    public_name = "Grade on sequence completion"

    summary_text = "Overall score is 0 if sequence is incomplete, and 1 once sequence is complete."

    detail_text = ("Score = 0.0 until sequence is completed, at which point the grade is 1.0 . This policy is designed "
                   "to encourage topic mastery and full sequence completion.")

    def _calculate(self):
        return float(self.sequence.completed)
