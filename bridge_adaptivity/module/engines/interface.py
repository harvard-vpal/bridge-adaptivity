from abc import ABCMeta, abstractmethod


class EngineInterface(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def select_activity(self, sequence):
        """
        Select activity from the collection by the adaptive engine.

        :param sequence: Sequence instance
        :return: selected activity source_launch_url
        """
        raise NotImplementedError("Adaptive Engine driver must implement this method.")

    @abstractmethod
    def sync_collection_activities(self, collection):
        """
        Synchronize Collection's Activities with the engine.

        :param collection: Collection instance to sync with the engine
        """
        raise NotImplementedError("Adaptive Engine driver must implement this method.")
