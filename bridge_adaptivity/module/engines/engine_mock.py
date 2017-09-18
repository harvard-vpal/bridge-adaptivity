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
        s_activities_list = list(sequence.items.exclude(score__isnull=True).values_list('activity_id', flat=True))
        available_activities = sequence.collection.activities.exclude(id__in=s_activities_list)
        pre_assesment = available_activities.filter(atype='A')
        generic = available_activities.filter(atype='G')
        post_assessment = available_activities.filter(atype='Z')
        chosen_activity_id = None
        if pre_assesment:
            chosen_activity_id = pre_assesment.first().id
        elif generic:
            chosen_activity_id = random.choice(generic).id
        elif post_assessment:
            chosen_activity_id = post_assessment.first().id
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
