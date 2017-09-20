import logging
import requests
import urlparse

from module.engines.interface import EngineInterface

log = logging.getLogger(__name__)


ACTIVITY_PARAMS = (
    'collection',
    'name',
    'tags',
    'type',
    'difficulty',
)

SEQUENCE_ITEM_PARAMS = (
    'learner',
    'activity',
    'score',
)

TYPES = {
    'A': 'pre-assessment',
    'Z': 'post-assessment'
}


class EngineVPAL(EngineInterface):
    """
    VPAL adaptive engine.

    To use VPAL engine with the Bridge for Adaptivity configure following parameters in the secure settings::

        ENGINE_MODULE = 'module.engines.engine_vpal'

        # ENGINE_DRIVER is a string with the name of driver class in the engine module
        ENGINE_DRIVER = 'EngineVPAL'

        # ENGINE_SETTINGS is a dict, with the initial params for driver initialization
        ENGINE_SETTINGS = {
            'BASE_URL': 'http://test.engine.vpal.io/engine/api',
        }
    """
    def __init__(self, **kwargs):
        self.host = kwargs.get('HOST')
        self.api_url = 'engine/api/'
        self.base_url = urlparse.urljoin(self.host, self.api_url)
        self.activity_url = urlparse.urljoin(self.base_url, "activity")

    @staticmethod
    def check_engine_response(engine_status, action=None, activity_name=None, status=200):
        if engine_status == status:
            log.debug("[VPAL Engine] activity {} is {} to the VPAL Engine.".format(activity_name, action))
            return True
        else:
            log.error("[VPAL Engine] activity {} is not {} to the VPAL Engine.".format(activity_name, action))
            return False

    @staticmethod
    def fulfil_payload(payload={}, instance_to_parse=None):
        from module.models import Activity, SequenceItem
        if isinstance(instance_to_parse, Activity):
            params = ACTIVITY_PARAMS
        elif isinstance(instance_to_parse, SequenceItem):
            params = SEQUENCE_ITEM_PARAMS
        else:
            raise ValueError("Payload for the instance {} cannot be prepared".format(instance_to_parse))
        for param in params:
            if param == 'type':
                atype = TYPES.get(getattr(instance_to_parse, 'atype'), 'generic')
                payload[param] = atype
            elif param == 'collection':
                collection = getattr(instance_to_parse, param).id
                payload[param] = collection
            else:
                payload[param] = getattr(instance_to_parse, param)
        return payload

    def combine_activity_url(self, activity):
        return urlparse.urljoin('{}/'.format(self.activity_url), str(activity.id))

    def select_activity(self, sequence):
        """
        VPAL engine provides recommended activity from the collection on the Bridge.

        :param sequence: sequence
        :return: selected activity_id
        """
        reco_url = urlparse.urljoin(
            "{}/".format(self.activity_url), "recommend?learner={user_id}&collection={collection_id}"
        ).format(user_id=sequence.lti_user.id, collection_id=sequence.collection.id)
        chosen_activity = requests.get(reco_url)
        if self.check_engine_response(chosen_activity.status_code, "chosen"):
            choose = chosen_activity.json()
            return choose.get('id')
        return None

    def add_activity(self, activity):
        """
        VPAL engine provides recommended activity from the collection to the Bridge.

        :param activity: Activity instance
        """
        payload = self.fulfil_payload({'id': activity.id}, activity)
        add_activity = requests.post(self.activity_url, json=payload)
        return self.check_engine_response(add_activity.status_code, 'added', activity.name, 201)

    def update_activity(self, activity):
        """
        VPAL engine update activity when it is updated on the Bridge.

        :param activity: Activity instance
        """
        payload = self.fulfil_payload(instance_to_parse=activity)
        update_activity = requests.patch(self.combine_activity_url(activity), json=payload)
        return self.check_engine_response(update_activity.status_code, 'updated', activity.name)

    def delete_activity(self, activity):
        """
        VPAL engine delete activity when it is deleted on the Bridge.

        :param activity: Activity instance
        """
        delete_activity = requests.delete(self.combine_activity_url(activity))
        return self.check_engine_response(delete_activity.status_code, 'deleted', activity.name, 204)

    def submit_activity_answer(self, sequence_item):
        """
        VPAL engine update student's answer for the activity in the sequence item.

        :param sequence_item: SequenceItem instance
        """
        submit_url = urlparse.urljoin(self.base_url, 'score')
        payload = self.fulfil_payload(instance_to_parse=sequence_item)
        submit_activity_score = requests.post(submit_url, json=payload)
        return self.check_engine_response(submit_activity_score.status_code, 'graded', sequence_item.activity.name)
