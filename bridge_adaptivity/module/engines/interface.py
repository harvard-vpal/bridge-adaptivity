from abc import ABCMeta, abstractmethod


class EngineInterface(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def select_activity(self, sequence):
        """
        Select activity from the collection by the adaptive engine

        :param sequence: Sequence instance
        :return: selected activity_id
        """
        raise NotImplementedError("Adaptive Engine driver must implement this method.")

    @abstractmethod
    def add_activity(self, activity):
        """
        Add the activity to the adaptive engine's collection

        :param activity: Activity instance
        """
        raise NotImplementedError("Adaptive Engine driver must implement this method.")

    @abstractmethod
    def update_activity(self, activity):
        """
        Update the activity in the adaptive engine's collection

        :param activity: Activity instance
        """
        raise NotImplementedError("Adaptive Engine driver must implement this method.")

    @abstractmethod
    def delete_activity(self, activity):
        """
        Delete the activity from the adaptive engine's collection

        :param activity: Activity instance
        """
        raise NotImplementedError("Adaptive Engine driver must implement this method.")

    @abstractmethod
    def submit_activity_answer(self, sequence_item):
        """
        Send student's answer to the adaptive engine.

        :param sequence_item: SequenceItem instance
        """
        raise NotImplementedError("Adaptive Engine driver must implement this method.")
