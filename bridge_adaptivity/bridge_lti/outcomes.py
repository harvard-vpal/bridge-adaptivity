import logging

from django.db.models import Count, Sum
from lti import OutcomeRequest

log = logging.getLogger(__name__)


def update_lms_grades(request, sequence, user_id):
    """Send grade update to LMS (LTI Tool)."""
    outcome_request = OutcomeRequest().from_post_request(request)

    outcome_service = sequence.outcome_service
    consumer = outcome_service.lms_lti_connection

    outcome_request.consumer_key = consumer.consumer_key
    outcome_request.consumer_secret = consumer.consumer_secret
    outcome_request.lis_outcome_service_url = outcome_service.lis_outcome_service_url
    outcome_request.lis_result_sourcedid = sequence.lis_result_sourcedid

    score = process_score(sequence)
    outcome_request.post_replace_result(score)
    lms_response = outcome_request.outcome_response
    if lms_response.is_success:
        log.info("Successfully sent updated grade to LMS. Student:{}, grade:{}, comment:{}".format(
            user_id, score, lms_response.code_major.text
        ))
    elif lms_response.is_processing:
        log.info("Grade update is being processed by LMS. Student:{}, grade:{}, comment:{}".format(
            user_id, score, lms_response.code_major.text
        ))
    elif lms_response.has_warning():
        log.warn("Grade update response has warnings. Student:{}, grade:{}, comment:{}".format(
            user_id, score, lms_response.code_major.text
        ))
    else:
        log.error("Grade update request failed. Student:{}, grade:{}, comment:{}".format(
            user_id, score, lms_response.code_major.text
        ))


def calculate_grade(trials_count, threshold, points_earned):
    """
    Grade calculation using current grade policy ("Grade Policy 1a", for now).

    Grade must be in {0.0 ... 1.0}

    :param (int) trials_count: grade policy 'N' argument
    :param (float) threshold: grade policy 'Q' argument
    :param (float) points_earned: grade policy 'P' argument
    :return: (float) grade
    """
    log.debug("Grade calculation args: N={%s}, Q={%s}, P={%s}", trials_count, threshold, points_earned)
    grade = points_earned / threshold if trials_count < threshold else points_earned / trials_count
    log.debug("Calculated grade: %s", grade)

    return grade


def process_score(sequence):
    """Calculate the score for the Sequence."""
    threshold = sequence.collection.threshold
    items_result = sequence.items.aggregate(points_earned=Sum('score'), trials_count=Count('score'))

    return calculate_grade(items_result['trials_count'], threshold, items_result['points_earned'])
