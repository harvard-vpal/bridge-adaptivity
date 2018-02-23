import logging
import random

from module.engines.interface import EngineInterface

log = logging.getLogger(__name__)


class EngineMock(EngineInterface):
    """Mock adaptive engine which is used by default if no other engines were added."""

    def select_activity(self, sequence):
        """
        Mock engine provides random choice for the activity from the collection on the Bridge.

        :param sequence: sequence
        :return: selected activity source_launch_url
        """
        s_activities_list = list(sequence.items.exclude(
            score__isnull=True,
            is_problem=True,
        ).values_list('activity_id', flat=True))
        available_activities = sequence.collection.activities.exclude(id__in=s_activities_list)
        pre_assesment = available_activities.filter(atype='A')
        generic = available_activities.filter(atype='G')
        post_assessment = available_activities.filter(atype='Z')
        chosen_activity_url = None
        if pre_assesment:
            chosen_activity_url = pre_assesment.first().source_launch_url
        elif generic:
            chosen_activity_url = random.choice(generic).source_launch_url
        elif post_assessment:
            chosen_activity_url = post_assessment.first().source_launch_url
        log.debug("Chosen activity is: {}".format(chosen_activity_url))
        return chosen_activity_url

    def sync_collection_activities(self, collection):
        """Mock engine works with data stored on the Bridge and do not need to implement method."""
        log.debug("The Collection {} was successfully synchronized with the Mock Engine.".format(
            collection.name
        ))
        return True

    def submit_activity_answer(self, sequence_item):
        """Mock engine works with data stored on the Bridge and do not need to implement method."""
        log.debug("Student has submitted answer for the activity {} and got {} scores.".format(
            sequence_item.activity.name, sequence_item.score
        ))
        return True
