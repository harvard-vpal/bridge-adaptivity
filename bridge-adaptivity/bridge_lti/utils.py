import hashlib

import shortuuid
from dce_lti_py import OutcomeRequest
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


def grade_passback(user_module, grade):
    '''
    Return grade data back to the LMS via LTI Outcome Service protocol
    '''
    if not grade:
        grade = user_module.grade

    # get LTI launch parameters for user module
    lti_parameters = user_module.ltiparameters

    # check if there is a url
    if not lti_parameters.lis_outcome_service_url:
        return None

    # construct a outcome request object
    outcome = OutcomeRequest({
        'lis_outcome_service_url': lti_parameters.lis_outcome_service_url,
        'lis_result_sourcedid': lti_parameters.lis_result_sourcedid,
        'consumer_key': lti_parameters.oauth_consumer_key,
        'consumer_secret': settings.LTI_OAUTH_CREDENTIALS[lti_parameters.oauth_consumer_key],
        'message_identifier': 'Grade from VPAL-Tutorgen LTI tool'
    })
    # send the outcome data
    outcome_response = outcome.post_replace_result(grade)

    return outcome_response


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
