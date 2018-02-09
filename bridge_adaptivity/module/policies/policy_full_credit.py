from .base import BaseGradingPolicy


class FullCreditOnCompleteGradingPolicy(BaseGradingPolicy):
    """Grading policy that gives full credit only on sequence completion, so that topic mastery is encouraged."""

    public_name = "Grade on sequence completion"

    def _calculate(self):
        return float(self.sequence.completed)
