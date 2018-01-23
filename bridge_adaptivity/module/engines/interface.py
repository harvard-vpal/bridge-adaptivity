from abc import ABCMeta, abstractmethod


class EngineInterface(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def select_activity(self, sequence):
        """
        Select activity from the collection by the adaptive engine.

        :param sequence: Sequence instance
        :return: selected activity_id
        """
        raise NotImplementedError("Adaptive Engine driver must implement this method.")

    @abstractmethod
    def submit_activity_answer(self, sequence_item):
        """
        Send student's answer to the adaptive engine.

        :param sequence_item: SequenceItem instance
        """
        raise NotImplementedError("Adaptive Engine driver must implement this method.")

    @abstractmethod
    def sync_collection_activities(self, collection_id, activities):
        """
        Synchronize Collection's Activities with the engine

        :param collection_id: ID of the collection to sync with the engine
        :param activities: QuerySet with Activities to update
        """
        raise NotImplementedError("Adaptive Engine driver must implement this method.")
