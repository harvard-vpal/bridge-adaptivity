import logging
import random

from module.engines.interface import EngineInterface

log = logging.getLogger(__name__)


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
        s_activities_list = list(sequence.items.values_list('activity_id', flat=True))
        available_activities = sequence.collection.activities.exclude(id__in=s_activities_list)
        chosen_activity_id = random.choice(available_activities).id if available_activities else None
        log.debug("Chosen activity is: {}".format(chosen_activity_id))
        return chosen_activity_id

    def add_activity(self, activity):
        """
        Mock engine works with data stored on the Bridge and do not need to implement method
        """
        log.debug("New activity {} is added to the Mock Engine.".format(activity))

    def update_activity(self, activity):
        """
        Mock engine works with data stored on the Bridge and do not need to implement method
        """
        log.debug("New activity {} is updated in the Mock Engine.".format(activity))

    def delete_activity(self, activity):
        """
        Mock engine works with data stored on the Bridge and do not need to implement method
        """
        log.debug("New activity {} is deleted from the Mock Engine.".format(activity))

    def submit_activity_answer(self, sequence_item):
        """
        Mock engine works with data stored on the Bridge and do not need to implement method
        """
        log.debug("Student has submitted answer for the activity {} and got {} scores.".format(
            sequence_item.activity.name, sequence_item.score
        ))
