# coding: utf-8
import requests

from bridge_lti.outcomes import update_lms_grades
from module.engines.engine_vpal import EngineVPAL
from .base import BaseGradingPolicy


class EngineGradedGradingPolicy(BaseGradingPolicy):
    """Grading policy class calculate grade based upon response from the engine."""

    public_name = 'Engine Graded'
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
        return self.sequence.group.engine_driver.get_grade(self.sequence)

    @classmethod
    def get_form_class(cls):
        from module.forms import BaseGradingPolicyForm
        return BaseGradingPolicyForm

    def send_grade(self):
        """Send grade to LMS system.

        Call update_lms_grades(self.context['request'], sequence=self.sequence, user_id=self.context['user_id'])
        :return: nothing.
        """
        if self.context.get('request'):
            update_lms_grades(self.context.get('request'), sequence=self.sequence, user_id=self.context['user_id'])
