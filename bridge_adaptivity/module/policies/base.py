# from module.models import Sequence, GradingPolicy as GradingPolicyModel
from django.db.models.aggregates import Sum, Count


class GradingPolicy(object):
    """Base grading policy class defines methods and variables of grading policy.
    >>> gp =  GradingPolicy(sequence=1, policy=2, b=3)
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

    public_name = 'Grading Policy'
    internal_name = 'policy_name'

    def __init__(self, sequence=None, policy=None, **kwargs):
        self.sequence = sequence
        self.policy = policy
        self.context = kwargs

    def _calculate(self):
        raise NotImplementedError('Method is not implemented.')

    def _get_points_earned_trials_count(self):
        """Get points earned and trials count from the sequence.

        :return tuple([trials_count, points_earned])"""
        items_result = self.sequence.items.aggregate(points_earned=Sum('score'), trials_count=Count('score'))
        return items_result['trials_count'], items_result['points_earned']

    @property
    def grade(self):
        return self._calculate()
