# coding: utf-8
from .base import BaseGradingPolicy


class FullCreditOnCompleteGradingPolicy(BaseGradingPolicy):
    """Grading policy that gives full credit only on sequence completion, so that topic mastery is encouraged."""

    public_name = "Full credit on complete"

    def _calculate(self):
        return self.sequence.completed
