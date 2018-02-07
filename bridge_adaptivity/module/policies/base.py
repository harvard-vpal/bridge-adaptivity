from abc import ABCMeta, abstractmethod

from django.db.models.aggregates import Count, Sum
from outcomes import update_lms_grades


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

    @classmethod
    def get_form_class(cls):
        from module.forms import BaseGradingPolicyForm
        return BaseGradingPolicyForm

    def __init__(self, sequence=None, policy=None, **kwargs):
        self.sequence = sequence
        self.policy = policy
        self.context = kwargs

    @abstractmethod
    def _calculate(self):
        raise NotImplementedError('Method is not implemented.')

    def _get_points_earned_trials_count(self):
        """Get points earned and trials count from the sequence.

        :return tuple([trials_count, points_earned])
        """
        items_result = self.sequence.items.aggregate(points_earned=Sum('score'), trials_count=Count('score'))
        return items_result['trials_count'], items_result['points_earned']

    @property
    def grade(self):
        return self._calculate()

    def send_grade(self, is_callback=False):
        """Send grade to LMS system.

        Call update_lms_grades(self.context['request'], sequence=self.sequence, user_id=self.context['user_id'])
        :param is_callback: is true if method called from callback_sequence_item_grade view, otherwise False
        :return: nothing.
        """
        if is_callback:
            update_lms_grades(self.context['request'], sequence=self.sequence, user_id=self.context['user_id'])
