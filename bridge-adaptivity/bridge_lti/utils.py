import hashlib
import string

import shortuuid
from django.conf import settings

REQUIRED_PARAMETERS = [
    'user_id', 'roles', 'context_id', 'oauth_version', 'oauth_consumer_key',
    'oauth_signature', 'oauth_signature_method', 'oauth_timestamp', 'oauth_nonce'
]

OPTIONAL_PARAMETERS = [
    'lis_result_sourcedid',
    'lis_outcome_service_url',
    'tool_consumer_instance_guid'
]


class LtiRole(object):
    """
    Constant for LTI roles.

    Reference: https://www.imsglobal.org/specs/ltiv1p1p1/implementation-guide#toc-11
    """
    LTI_ROLES = {
        "Learner": {"learner", "student"},
        "Instructor": {"instructor"},
        "Administrator": {"administrator"},
        "TeachingAssistant": {"teachingassistant"},
        "ContentDeveloper": {"contentdeveloper"},
        "Mentor": {"mentor"}
    }

    def __init__(self, roles_param):
        self.roles = map(string.lower, roles_param.split(",")) if roles_param else []

    @property
    def is_undefined(self):
        return not bool(self.roles)

    @property
    def is_learner(self):
        return self.LTI_ROLES["Learner"].intersection(self.roles)

    @property
    def is_instructor(self):
        return self.LTI_ROLES["Instructor"].intersection(self.roles)

    @property
    def is_administrator(self):
        return self.LTI_ROLES["Administrator"].intersection(self.roles)

    @property
    def is_assistant(self):
        return self.LTI_ROLES["TeachingAssistant"].intersection(self.roles)

    @property
    def is_content_developer(self):
        return self.LTI_ROLES["ContentDeveloper"].intersection(self.roles)

    @property
    def is_mentor(self):
        return self.LTI_ROLES["Mentor"].intersection(self.roles)


def short_token():
    """
    Generate a hash that can be used as lti consumer key.
    """
    hash = hashlib.sha1(shortuuid.uuid())
    hash.update(settings.SECRET_KEY)
    return hash.hexdigest()[::2]


def get_required_params(dictionary, additional_params=None):
    """
    Extract all required LTI parameters from a dict and check for completeness.

    :param dictionary: contains all required parameters.
    :param additional_params: any other expected parameters.
    :return: dict: containing all the required parameters from the original dictionary and additional parameters,
    or None if any expected parameters are missing.
    """
    params = {}
    additional_params = additional_params or []
    for key in REQUIRED_PARAMETERS + additional_params:
        if key not in dictionary:
            return None
        params[key] = dictionary[key]
    return params


def get_optional_params(dictionary):
    """
    Extract all optional LTI parameters from a dictionary.

    :param dictionary: dict containing zero or more optional parameters.
    :return: dict containing all optional parameters from the original dictionary,
    or an empty dict if no optional parameters were present.
    """
    return {key: dictionary[key] for key in OPTIONAL_PARAMETERS if key in dictionary}
