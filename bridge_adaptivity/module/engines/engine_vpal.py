import logging
import urlparse

import requests

from module.engines.interface import EngineInterface

log = logging.getLogger(__name__)


ACTIVITY_PARAMS = (
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
            'HOST': 'https://example.com',
            'TOKEN': 'very_secure_token',
        }
    """

    def __init__(self, **kwargs):
        self.host = kwargs.get('HOST')
        self.api_url = 'engine/api/'
        self.base_url = urlparse.urljoin(self.host, self.api_url)
        self.activity_url = urlparse.urljoin(self.base_url, "activity")
        token = kwargs.get('TOKEN')
        self.headers = {'Authorization': 'Token {}'.format(token)} if token else {}

    @staticmethod
    def check_engine_response(engine_status, action=None, obj=None, status=200):
        if engine_status == status:
            log.debug("[VPAL Engine] {} is {}.".format(obj, action))
            return True
        else:
            log.error("[VPAL Engine] {} is not {}.".format(obj, action))
            return False

    def fulfill_payload(self, payload={}, instance_to_parse=None):
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
            elif param == 'learner':
                learner = instance_to_parse.sequence.lti_user.id
                payload[param] = learner
            elif param == 'activity':
                payload[param] = getattr(instance_to_parse, param).id
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
        log.warn("VPAL RECO URL: {}".format(reco_url))
        chosen_activity = requests.get(reco_url, headers=self.headers)
        if self.check_engine_response(chosen_activity.status_code, action="chosen", obj='activity'):
            choose = chosen_activity.json()
            return choose.get('id')
        return None

    def submit_activity_answer(self, sequence_item):
        """
        VPAL engine update student's answer for the activity in the sequence item.

        :param sequence_item: SequenceItem instance
        """
        submit_url = urlparse.urljoin(self.base_url, 'score')
        payload = self.fulfill_payload(instance_to_parse=sequence_item)
        submit_activity_score = requests.post(submit_url, json=payload, headers=self.headers)
        return self.check_engine_response(submit_activity_score.status_code, action='graded', obj='sequence item')

    def sync_collection_activities(self, collection_id, activities):
        """
        VPAL engine synchronize Collection's Activities

        :param collection_id: ID of the collection for synchronization
        :param activities: QuerySet with Activities to update
        """
        sync_url = urlparse.urljoin(self.base_url, 'sync/collection/{}'.format(collection_id))
        payload = {"collection": collection_id, "activities": []}
        for activity in activities:
            payload["activities"].append(self.fulfill_payload(instance_to_parse=activity))
        sync_collection = requests.post(sync_url, json=payload, headers=self.headers)
        return self.check_engine_response(sync_collection.status_code, action='synchronized', obj='collection')
