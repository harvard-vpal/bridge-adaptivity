import random

from module.engines.engine_interface import EngineInterface
from module.models import Collection, Sequence


class EngineMock(EngineInterface):
    """
    Mock adaptive engine which is used by default if no other engines were added.
    """
    def select_activity(self, sequence):
        """
        Mock engine provides random choice for the activity from the collection on the Bridge

        :param sequence: sequence
        :return: selected activity_id
        """
        s_activities_list = list(sequence.sequenceitem_set.values_list('activity_id', flat=True))
        available_activities = sequence.collection.activity_set.exclude(id__in=s_activities_list)
        return random.choice(available_activities).id if available_activities else None

    def add_activity(self, activity_id):
        """
        Mock engine works with data stored on the Bridge and do not need to implement method
        """
        pass

    def update_activity(self, activity_id):
        """
        Mock engine works with data stored on the Bridge and do not need to implement method
        """
        pass

    def delete_activity(self, activity_id):
        """
        Mock engine works with data stored on the Bridge and do not need to implement method
        """
        pass
