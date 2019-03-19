import copy
import logging
import urllib.parse

import requests

from module.engines.interface import EngineInterface

log = logging.getLogger(__name__)


ACTIVITY_PARAMS = (
    'name',
    'tags',
    'type',
    'difficulty',
    'source_launch_url',
    'repetition',
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

VALID_STATUSES = [200, 201]


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
        self.api_url = 'api/v2/'
        self.base_url = urllib.parse.urljoin(self.host, self.api_url)
        self.activity_url = urllib.parse.urljoin(self.base_url, "activity")
        token = kwargs.get('TOKEN')
        self.headers = {'Authorization': 'Token {}'.format(token)} if token else {}

    @staticmethod
    def check_engine_response(request, action=None, obj=None, name=None, status=VALID_STATUSES):
        if obj and name:
            obj += ' {}'.format(name)
        if request.status_code in status:
            log.debug("[VPAL Engine] {} is {}.".format(obj, action))
            return True
        else:
            log.error("[VPAL Engine] {} is not {}.".format(obj, action))
            log.error("[VPAL Engine] Error response: {}".format(request.text))
            return False

    def fulfill_payload(self, payload=None, instance_to_parse=None, score=None):
        if payload is None:
            payload = {}
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
            elif param == 'learner':  # instance_to_parse == SequenceItem
                self.add_learner_to_payload(instance_to_parse.sequence, payload)
            elif param == 'activity':
                payload[param] = getattr(instance_to_parse, param).source_launch_url
            else:
                payload[param] = getattr(instance_to_parse, param)
        return payload

    @staticmethod
    def add_learner_to_payload(sequence, payload, add_metadata=True):
        """
        Update payload with the 'learner' parameter.

        :param sequence: Sequence instance
        :param payload: payload to update
        :param add_metadata: boolean flag to add sequence's metadata to the payload, default is True
        :return: updated payload
        """
        metadata = copy.deepcopy(sequence.metadata)
        tool_consumer_instance_guid = None
        if metadata:
            # NOTE(idegtiarov) Check metadata for the `tool_consumer_instance_guid` if it is found pop it to update
            # `learner` param in the payload in accordance with the documentation
            tool_consumer_instance_guid = metadata.pop('tool_consumer_instance_guid', None)
            payload.update(metadata if add_metadata else {})  # payload is updated with the lti parameters
        payload.update({
            "learner": {
                'user_id': sequence.lti_user.user_id,
                'tool_consumer_instance_guid': (
                    tool_consumer_instance_guid or sequence.lti_user.lti_lms_platform.consumer_name
                ),
            }
        })
        return payload

    def combine_activity_url(self, activity):
        return urllib.parse.urljoin('{}/'.format(self.activity_url), str(activity.id))

    def select_activity(self, sequence):
        """
        VPAL engine provides recommended activity from the collection on the Bridge.

        :param sequence: sequence
        :return: selected activity source_launch_url
        """
        reco_url = urllib.parse.urljoin(
            "{}/".format(self.activity_url), "recommend"
        )
        payload = {"collection": sequence.collection_order.collection.slug, "sequence": []}
        self.add_learner_to_payload(sequence, payload)

        for sequence_item in sequence.items.all():
            payload["sequence"].append(self.fulfill_payload(payload={}, instance_to_parse=sequence_item))
        chosen_activity = requests.post(reco_url, headers=self.headers, json=payload)
        if self.check_engine_response(chosen_activity, action="chosen", obj='activity'):
            choose = chosen_activity.json()
            return choose

    def sync_collection_activities(self, collection):
        """
        VPAL engine synchronize Collection's Activities.

        :param collection: Collection instance for synchronization
        """
        sync_url = urllib.parse.urljoin(self.base_url, 'collection/{}/activities'.format(collection.slug))
        payload = []
        for activity in collection.activities.all():
            payload.append(self.fulfill_payload(payload={}, instance_to_parse=activity))
        sync_collection = requests.post(sync_url, json=payload, headers=self.headers)
        return self.check_engine_response(
            sync_collection, action='synchronized', obj='collection', name=collection.name
        )

    def submit_activity_answer(self, sequence_item):
        """
        VPAL engine update student's answer for the activity in the sequence item.

        :param sequence_item: SequenceItem instance
        """
        submit_url = urllib.parse.urljoin(self.base_url, 'score')
        payload = self.fulfill_payload(instance_to_parse=sequence_item, score=True)
        self.add_learner_to_payload(sequence_item.sequence, payload, add_metadata=False)
        submit_activity_score = requests.post(submit_url, json=payload, headers=self.headers)
        return self.check_engine_response(
            submit_activity_score,
            action='graded',
            obj='sequence item',
            name=sequence_item.activity.name,
        )

    def get_grade(self, sequence):
        """
        Get grade from the VPAL engine for particular collection.

        :param sequence: Sequence instance
        :return: grade returned from engine
        """
        url = urllib.parse.urljoin(self.base_url, 'collection/{collection_slug}/grade'.format(
            collection_slug=sequence.collection_order.collection.slug)
        )
        response = requests.post(url, json=self.add_learner_to_payload(sequence, {}), headers=self.headers)
        if self.check_engine_response(response, action='grade', obj='sequence'):
            grade = response.json().get('grade')
            if 0 <= grade <= 1:
                return grade
        return None
