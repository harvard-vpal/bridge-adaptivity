from django.http import Http404
from django.shortcuts import get_object_or_404
from lxml import etree

from module import ENGINE
from module.models import Activity


class BridgeError(Exception):
    pass


XML = u"""<?xml version="1.0" encoding="UTF-8"?>
          <imsx_POXEnvelopeResponse xmlns = "http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">
              <imsx_POXHeader>
                  <imsx_POXResponseHeaderInfo>
                      <imsx_version>V1.0</imsx_version>
                      <imsx_messageIdentifier>{imsx_messageIdentifier}</imsx_messageIdentifier>
                      <imsx_statusInfo>
                          <imsx_codeMajor>{imsx_codeMajor}</imsx_codeMajor>
                          <imsx_severity>status</imsx_severity>
                          <imsx_description>{imsx_description}</imsx_description>
                          <imsx_messageRefIdentifier>
                          </imsx_messageRefIdentifier>
                      </imsx_statusInfo>
                  </imsx_POXResponseHeaderInfo>
              </imsx_POXHeader>
              <imsx_POXBody>{response}</imsx_POXBody>
          </imsx_POXEnvelopeResponse>
"""


def _find_param_from_xml(root, param, namespaces, text=True):
    """
    Auxiliary function

    :param root: etree created from the xml
    :param param: required parameter
    :param namespaces: namespace is specified in the LTI spec
    :param text: boolean flag for text part from searching xml param
    :return: string value of the param witch is found in root
    """
    try:
        result = root.xpath("//def:{}".format(param), namespaces=namespaces)[0]
        return result.text if text else result
    except IndexError:
        raise BridgeError('Failed to parse {} from the XML request body'.format(param))


def parse_callback_grade_xml(body):
    """
    Parses values from the Source Outcome Service XML.

    (Function is based on the solution from https://github.com/edx/xblock-lti-consumer)

    XML body should contain nsmap with namespace, that is specified in LTI specs.

    Arguments:
        body (str): XML Outcome Service request body

    Returns:
        tuple: imsx_message_identifier, sourced_id, score, action

    Raises:
        BribgeError
            if submitted score is outside the permitted range
            if the XML is missing required entities
            if there was a problem parsing the XML body
    """
    lti_spec_namespace = "http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0"
    namespaces = {'def': lti_spec_namespace}
    data = body.strip().encode('utf-8')

    try:
        parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
        root = etree.fromstring(data, parser=parser)
    except etree.XMLSyntaxError as ex:
        raise (ex.message or 'Body is not the valid XML')
    body = _find_param_from_xml(root, 'imsx_POXBody', namespaces, text=False)
    try:
        action = body.getchildren()[0].tag.replace('{' + lti_spec_namespace + '}', '')
    except IndexError:
        raise BridgeError('Failed to parse action from XML request body')

    imsx_message_identifier = _find_param_from_xml(root, 'imsx_messageIdentifier', namespaces)
    sourced_id = _find_param_from_xml(root, 'sourcedId', namespaces)
    score = _find_param_from_xml(root, 'textString', namespaces)

    # Raise exception if score is not float or not in range 0.0-1.0 regarding documentation
    # SEE http://www.imsglobal.org/specs/ltiv1p1p1/implementation-guide
    score = float(score)
    if not 0.0 <= score <= 1.0:
        raise BridgeError('score value outside the permitted range of 0.0-1.0')

    return imsx_message_identifier, sourced_id, score, action


def chose_activity(sequence_item=None, sequence=None):
    sequence = sequence or sequence_item.sequence

    try:
        activity_id = ENGINE.select_activity(sequence)
        return get_object_or_404(Activity, pk=activity_id)
    except (IndexError, Http404):
        sequence_item.sequence.completed = True
        sequence_item.sequence.save()
        return None
