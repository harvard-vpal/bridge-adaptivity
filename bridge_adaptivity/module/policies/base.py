from abc import ABCMeta, abstractmethod

from django.db.models.aggregates import Count, Sum

from bridge_lti.outcomes import update_lms_grades


class BaseGradingPolicy(object):
    """Base grading policy class defines methods and variables of grading policy.

    >>> gp =  BaseGradingPolicy(sequence=1, policy=2, b=3)
    >>> gp.sequence
    1
    >>> gp.context['b']
    3
    >>> gp.public_name
    'Grading Policy'
    >>> gp.internal_name
    'policy_name'
    >>> gp()
    Traceback (most recent call last):
        ...
    NotImplementedError: Method is not implemented.
    """

    __metaclass__ = ABCMeta

    public_name = 'Grading Policy'
    require = {}

    def __init__(self, sequence=None, policy=None, **kwargs):
        self.sequence = sequence
        self.policy = policy
        self.context = kwargs

    @classmethod
    def get_form_class(cls):
        from module.forms import BaseGradingPolicyForm
        return BaseGradingPolicyForm

    @abstractmethod
    def _calculate(self):
        raise NotImplementedError('Method is not implemented.')

    def _get_points_earned_trials_count(self):
        """Get points earned and trials count from the sequence.

        :return tuple([trials_count, points_earned])
        """
        items_result = self.sequence.items.aggregate(
            points_earned=Sum('score'), trials_count=Count('score')
        )
        return items_result['trials_count'], items_result['points_earned']

    @property
    def grade(self):
        return self._calculate()

    def _send_grade(self, with_request=False):
        """Send grade to LMS system.

        Call update_lms_grades(self.context['request'], sequence=self.sequence, user_id=self.context['user_id'])
        :return: nothing.
        """
        if with_request:
            update_lms_grades(self.context.get('request'), sequence=self.sequence, user_id=self.context['user_id'])
        else:
            update_lms_grades(sequence=self.sequence, user_id=self.context['user_id'])

    def send_grade(self):
        return self._send_grade()
