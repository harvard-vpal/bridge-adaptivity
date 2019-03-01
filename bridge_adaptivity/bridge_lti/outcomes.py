import logging

from lti import OutcomeRequest

log = logging.getLogger(__name__)


def update_lms_grades(request=None, sequence=None):
    """Send grade update to LMS (LTI Tool)."""
    outcome_request = OutcomeRequest().from_post_request(request) if request else OutcomeRequest()

    outcome_service = sequence.outcome_service
    if outcome_service is None:
        log.info(f"Sequence: {sequence} doesn't contain an outcome service, grade is not sent.")
        return
    consumer = outcome_service.lms_lti_connection

    outcome_request.consumer_key = consumer.consumer_key
    outcome_request.consumer_secret = consumer.consumer_secret
    outcome_request.lis_outcome_service_url = outcome_service.lis_outcome_service_url
    outcome_request.lis_result_sourcedid = sequence.lis_result_sourcedid

    log.debug("Update LMS grades. Used sequence = {} is completed = {}, grading_policy = {}".format(
        sequence, sequence.completed, sequence.collection_order.grading_policy
    ))

    score = sequence.collection_order.grading_policy.calculate_grade(sequence)
    outcome_request.post_replace_result(score)
    lms_response = outcome_request.outcome_response
    user_id = sequence.lti_user
    if lms_response.is_success():
        log.info("Successfully sent updated grade to LMS. Student:{}, grade:{}, comment: success".format(
            user_id, score
        ))
    elif lms_response.is_processing():
        log.info("Grade update is being processed by LMS. Student:{}, grade:{}, comment: processing".format(
            user_id, score
        ))
    elif lms_response.has_warning():
        log.warning("Grade update response has warnings. Student:{}, grade:{}, comment: warning".format(
            user_id, score
        ))
    else:
        log.error("Grade update request failed. Student:{}, grade:{}, comment:{}".format(
            user_id, score, lms_response.code_major
        ))
