from dce_lti_py import OutcomeRequest
from django.conf import settings


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
        'lis_outcome_service_url':lti_parameters.lis_outcome_service_url,
        'lis_result_sourcedid':lti_parameters.lis_result_sourcedid,
        'consumer_key': lti_parameters.oauth_consumer_key,
        'consumer_secret': settings.LTI_OAUTH_CREDENTIALS[lti_parameters.oauth_consumer_key],
        'message_identifier': 'Grade from VPAL-Tutorgen LTI tool'
    })
    # send the outcome data
    outcome_response = outcome.post_replace_result(grade)

    return outcome_response
