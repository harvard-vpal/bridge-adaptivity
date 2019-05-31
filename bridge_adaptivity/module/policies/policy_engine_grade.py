# coding: utf-8
from module.engines.engine_vpal import EngineVPAL
from .base import BaseGradingPolicy


class EngineGradedGradingPolicy(BaseGradingPolicy):
    """Grading policy class calculate grade based upon response from the engine."""

    public_name = 'Engine Graded'
    summary_text = 'Engine grading policy.'
    detail_text = 'This policy asks chosen engine to provide the grade for the sequence.'
    require = {
        'engine': (EngineVPAL,),
    }

    def _get_points_earned_trials_count(self):
        """Get points earned and trials count from the sequence.

        :return tuple([trials_count, points_earned])
        """
        pass

    def _calculate(self):
        """
        Send request to engine and get response with grade.

        :return: received grade from engine.
        """
        return self.sequence.collection_order.engine.engine_driver.get_grade(self.sequence)

    @classmethod
    def get_form_class(cls):
        from module.forms import BaseGradingPolicyForm
        return BaseGradingPolicyForm

    def send_grade(self):
        """Send grade to LMS system.

        :return: nothing.
        """
        self._send_grade(with_request=True)
