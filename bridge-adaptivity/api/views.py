import logging

from django.http import HttpResponseBadRequest
from django.http import HttpResponseNotFound
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from slumber.exceptions import HttpClientError, HttpNotFoundError

from api.backends.openedx import OpenEdxApiClient
from bridge_lti.models import LtiConsumer

log = logging.getLogger(__name__)


def apply_data_filter(data, filters=None):
    """
    Filter for `blocks` OpenEdx Course API response.

    Picks data which is listed in `filters` only.
    :param data: (dict)
    :param filters:
    :return:
    """
    if filters is None:
        return data

    filtered_data = {}
    for block_name, block_value in data.items():
        filtered_block_value = {k: v for k, v in block_value.items() if k in filters}
        filtered_data[block_name] = filtered_block_value

    return filtered_data


@csrf_exempt
@require_http_methods(["POST"])
def get_sources(request):
    """
    Content Source API requester.

    Uses OpenEdx Course API v.1.0
    :param request:
    :param course_id:
    :return: (JSON) blocks
    """
    course_id = request.POST.get('course_id')
    if not course_id:
        return HttpResponseBadRequest(content={"error": "`course_id` is a mandatory parameter."})

    log.debug('course_ID{}'.format(course_id))
    try:
        # TODO: multiple ContentSources processing - one, for now.
        content_source = LtiConsumer.objects.filter(is_active=True).first()
        log.debug('Picked content Source: {}'.format(content_source.name))
    except LtiConsumer.DoesNotExist:
        return HttpResponseBadRequest(content={"error": "There are no Content Sources for now."})

    # Get API client instance:
    api = OpenEdxApiClient(content_source=content_source)

    try:
        # TODO: multiple Courses processing - one, for now.
        blocks = api.get_course_blocks(course_id)
        filtered_blocks = apply_data_filter(blocks, filters=['id', 'block_id', 'display_name', 'lti_url'])
    except HttpNotFoundError:
        return HttpResponseNotFound(content={"error": "Requested course not found. Check `course_id` url encoding."})
    except HttpClientError:
        return HttpResponseBadRequest(content={"error": "Not valid query."})

    data = filtered_blocks or {}
    return JsonResponse(data=data)


