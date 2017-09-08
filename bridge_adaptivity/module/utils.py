from lxml import etree


class BridgeError(Exception):
    pass


def _find_param_from_xml(root, param, namespaces):
    """
    Auxiliary function

    :param root: etree created from the xml
    :param param: required parameter
    :param namespaces: namespace is specified in the LTI spec
    :return: string value of the param witch is found in root
    """
    try:
        return root.xpath("//def:{}".format(param), namespaces=namespaces)[0].text
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
        tuple: sourcedId, score

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

    sourced_id = _find_param_from_xml(root, 'sourcedId', namespaces)
    score = _find_param_from_xml(root, 'textString', namespaces)

    # Raise exception if score is not float or not in range 0.0-1.0 regarding documentation
    # SEE http://www.imsglobal.org/specs/ltiv1p1p1/implementation-guide
    score = float(score)
    if not 0.0 <= score <= 1.0:
        raise BridgeError('score value outside the permitted range of 0.0-1.0')

    return sourced_id, score
