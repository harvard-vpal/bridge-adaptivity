"""
Based on OpenEdx lti_provider application.
Helper functions for managing interactions with the LTI outcomes service defined in LTI v1.1.
"""

import logging
import uuid

import requests
import requests_oauthlib
from lxml import etree
from lxml.builder import ElementMaker
from requests.exceptions import RequestException

from bridge_lti.models import OutcomeService

log = logging.getLogger(__name__)


def store_outcome_parameters(request_params, sequence, lti_consumer):
    """
    Save outcome related LTI parameters to sent outcome info later.

    Determine whether a set of LTI launch parameters contains information about an expected score.
    Create a new OutcomeService record if none exists for the tool consumer, and update any
    incomplete record with additional data if it is available.
    """
    result_id = request_params.get('lis_result_sourcedid', None)

    # NOTE(wowkalucky): We're only interested in requests that include a lis_result_sourcedid parameter.
    # An LTI consumer that doesn't send that parameter does not expect scoring updates for that particular request.
    log.debug("OutcomeService: storing outcome parameters...")
    if result_id:
        log.debug("result_id: %s", result_id)
        result_service = request_params.get('lis_outcome_service_url', None)
        if not result_service:
            log.warn(
                "OutcomeService: `lis_outcome_service_url` parameter missing from scored assignment;"
                "we will be unable to return a score. Request parameters: %s",
                request_params
            )
            return

        outcomes, __ = OutcomeService.objects.get_or_create(
            lis_outcome_service_url=result_service,
            lms_lti_connection=lti_consumer
        )

        sequence.lis_result_sourcedid = result_id
        sequence.outcome_service = outcomes
        sequence.save()


def send_score_update(sequence, score):
    """
    Create and send the XML message to the campus LMS system to update the grade for Sequence.

    1) build XML;
    2) sign with OAuth signature and send;
    3) receive response and parse it.
    """
    log.debug("Sending score[%s] update...", score)
    xml = generate_replace_result_xml(sequence.lis_result_sourcedid, score)

    try:
        response = sign_and_send_replace_result(sequence, xml)
    except RequestException:
        response = None
        log.exception("OutcomeService: Error when sending result.")

    # NOTE(wowkalucky): If something went wrong, make sure that we have a complete log record.
    # NOTE(wowkalucky): That way we can manually fix things up on the campus system later if necessary.
    if not (response and check_replace_result_response(response)):
        log.error(
            "OutcomeService: Failed to update score on LTI consumer. "
            "LtiUser: %s, Sequence: %s, score: %s, status: %s, body: %s",
            sequence.lti_user,
            sequence,
            score,
            response,
            response.text if response else 'Unknown'
        )


def generate_replace_result_xml(result_sourcedid, score):
    """
    Create the XML document that contains the new score.

    This new score to be sent to the LTI consumer.
    The format of this message is defined in the LTI 1.1 spec.
    """
    log.debug("...generating score xml")
    elem = ElementMaker(nsmap={None: 'http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0'})

    xml = elem.imsx_POXEnvelopeRequest(
        elem.imsx_POXHeader(
            elem.imsx_POXRequestHeaderInfo(
                elem.imsx_version('V1.0'),
                elem.imsx_messageIdentifier(str(uuid.uuid4()))
            )
        ),
        elem.imsx_POXBody(
            elem.replaceResultRequest(
                elem.resultRecord(
                    elem.sourcedGUID(
                        elem.sourcedId(result_sourcedid)
                    ),
                    elem.result(
                        elem.resultScore(
                            elem.language('en'),
                            elem.textString(str(score))
                        )
                    )
                )
            )
        )
    )
    return etree.tostring(xml, xml_declaration=True, encoding='UTF-8')


def sign_and_send_replace_result(sequence, xml):
    """
    OAuth xml processing.

    Take the XML document generated in generate_replace_result_xml.
    Sign it with the consumer key and secret assigned to the consumer.
    Send the signed message to the LTI consumer.
    """
    log.debug("...signing generated xml with consumer signature")
    outcome_service = sequence.outcome_service
    consumer = outcome_service.lms_lti_connection
    consumer_key = consumer.consumer_key
    consumer_secret = consumer.consumer_secret

    # NOTE(wowkalucky): calculate the OAuth signature:
    oauth = requests_oauthlib.OAuth1(
        consumer_key,
        consumer_secret,
        signature_method='HMAC-SHA1',
        force_include_body=True
    )

    headers = {'content-type': 'application/xml'}
    log.debug("...sending signed score update")
    response = requests.post(
        outcome_service.lis_outcome_service_url,
        data=xml,
        auth=oauth,
        headers=headers
    )

    return response


def check_replace_result_response(response):
    """
    Outcome service response analyzer.

    Parse the response sent by the LTI consumer after an score update message
    has been processed. Return True if the message was properly received, or
    False if not. The format of this message is defined in the LTI 1.1 spec.
    """
    log.debug("...checking `score update` response")
    if not response.ok:
        log.error(
            "OutcomeService responded with error: status code %s",
            response.status_code
        )
        return False

    xml = response.content
    try:
        root = etree.fromstring(xml)
    except etree.ParseError:
        log.exception("OutcomeService: failed to parse response XML: %s", xml)
        return False

    major_codes = root.xpath(
        '//ns:imsx_codeMajor',
        namespaces={'ns': 'http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0'}
    )

    if len(major_codes) != 1:
        log.error(
            "OutcomService response: Expected exactly one 'imsx_codeMajor' field in response. Received %s",
            major_codes
        )
        return False

    if major_codes[0].text != 'success':
        failure_description = root.xpath(
            '//ns:imsx_description',
            namespaces={'ns': 'http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0'}
        )[0].text
        log.error(
            "OutcomeService response: unexpected major code: %s (%s)",
            major_codes[0].text,
            failure_description
        )
        return False

    log.debug("...score successfully updated!")
    return True


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
    grade = points_earned/threshold if trials_count < threshold else points_earned/trials_count
    log.debug("Calculated grade: {%s}", grade)

    return grade
