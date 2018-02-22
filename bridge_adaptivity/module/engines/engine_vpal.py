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
    'source_launch_url',
)

SEQUENCE_ITEM_PARAMS = [
    'activity',
    'score',
    'is_problem',
]

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
    def check_engine_response(engine_status, action=None, obj=None, name=None, status=200):
        if obj and name:
            obj += ' {}'.format(name)
        if engine_status == status:
            log.debug("[VPAL Engine] {} is {}.".format(obj, action))
            return True
        else:
            log.error("[VPAL Engine] {} is not {}.".format(obj, action))
            return False

    def fulfill_payload(self, payload={}, instance_to_parse=None, score=None):
        from module.models import Activity, SequenceItem
        if isinstance(instance_to_parse, Activity):
            params = ACTIVITY_PARAMS
        elif isinstance(instance_to_parse, SequenceItem):
            params = SEQUENCE_ITEM_PARAMS
            if score:
                params[-1] = 'learner'  # A hook, while VPAL is interesting in the grades on student's answers
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
                payload[param] = getattr(instance_to_parse, param).source_launch_url
            else:
                payload[param] = getattr(instance_to_parse, param)
        return payload

    def combine_activity_url(self, activity):
        return urlparse.urljoin('{}/'.format(self.activity_url), str(activity.id))

    def select_activity(self, sequence):
        """
        VPAL engine provides recommended activity from the collection on the Bridge.

        :param sequence: sequence
        :return: selected activity source_launch_url
        """
        reco_url = urlparse.urljoin(
            "{}/".format(self.activity_url), "recommend"
        )
        payload = {"learner": sequence.lti_user.id, "collection": sequence.collection.id, "sequence": []}
        if sequence.metadata:
            payload.update(sequence.metadata)  # payload is updated with the lti parameters
        for sequence_item in sequence.items.all():
            payload["sequence"].append(self.fulfill_payload(payload={}, instance_to_parse=sequence_item))
        chosen_activity = requests.post(reco_url, headers=self.headers, json=payload)
        if self.check_engine_response(chosen_activity.status_code, action="chosen", obj='activity'):
            choose = chosen_activity.json()
            return choose.get('source_launch_url')
        return None

    def sync_collection_activities(self, collection):
        """
        VPAL engine synchronize Collection's Activities.

        :param collection: Collection instance for synchronization
        """
        sync_url = urlparse.urljoin(self.base_url, 'collection/{}/activities'.format(collection.id))
        payload = []
        for activity in collection.activities.all():
            payload.append(self.fulfill_payload(payload={}, instance_to_parse=activity))
        sync_collection = requests.post(sync_url, json=payload, headers=self.headers)
        return self.check_engine_response(
            sync_collection.status_code, action='synchronized', obj='collection', name=collection.name, status=201
        )

    def submit_activity_answer(self, sequence_item):
        """
        VPAL engine update student's answer for the activity in the sequence item.

        :param sequence_item: SequenceItem instance
        """
        submit_url = urlparse.urljoin(self.base_url, 'score')
        payload = self.fulfill_payload(instance_to_parse=sequence_item, score=True)
        submit_activity_score = requests.post(submit_url, json=payload, headers=self.headers)
        return self.check_engine_response(
            submit_activity_score.status_code,
            action='graded',
            obj='sequence item',
            name=sequence_item.activity.name,
            status=201,
        )
