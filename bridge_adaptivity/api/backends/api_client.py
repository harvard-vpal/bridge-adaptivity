from collections import defaultdict
import logging

from django.utils.translation import ugettext as _
from slumber.exceptions import HttpClientError, HttpNotFoundError

from api.backends.base_api_client import BaseApiClient
from api.backends.dart_api_client import DartApiClient
from api.backends.edx_api_client import OpenEdxApiClient
from bridge_lti.models import LtiContentSource

log = logging.getLogger(__name__)


def api_client_factory(content_source: LtiContentSource) -> BaseApiClient:
    """
    Return API client for the given content source.
    """
    api_clients = {
        LtiContentSource.EDX_SOURCE: OpenEdxApiClient,
        LtiContentSource.DART: DartApiClient,
        LtiContentSource.BASE_SOURCE: BaseApiClient,
    }
    return api_clients[content_source.source_type](content_source)


def get_active_content_sources(request, source_ids=None, not_allow_empty_source_id=True):
    """
    Check that passed source_id parameter is valid.

    If there's only one active source provider - source_id parameter is not required, it will get first active.
    :param request: Request object
    :param source_ids: LtiContentSource object id or list of this objects
    :param not_allow_empty_source_id: if True - it will not allow empty source_id, if False - source_id could be None
    :return: queryset of content_sources
    :raise HttpClientError: if provided parameters are not valid
    """
    if not_allow_empty_source_id and not source_ids:
        # if source_id is not provided and more than one active content_provider
        raise HttpClientError(_("Parameter source_id is mandatory if there's more than one active content source."))

    content_sources = get_content_providers(request, source_ids=source_ids)

    return content_sources


def get_available_blocks(request, source_id, course_id=''):
    """
    Content Source API requester.

    Fetches all source blocks from the course with the given ID.
    Blocks data is filtered by `apply_data_filter`.
    :param request: Request object
    :param course_id: Course id
    :param source_id: LtiContentSource id
    :return: (list) blocks data
    """
    content_source = get_active_content_sources(request, source_id).first()
    all_blocks = []

    # Get API client instance:
    api = api_client_factory(content_source=content_source)
    try:
        # filter function will be applied to api response
        all_blocks.extend(
            apply_data_filter(
                api.get_course_blocks(course_id),
                filters=[
                    'id',
                    'block_id',
                    'display_name',
                    'lti_url',
                    'type',
                    'content_source_id',
                    'visible_to_staff_only',
                ],
                context_id=course_id,
                content_source_id=content_source.id
            )
        )
    except HttpNotFoundError:
        raise HttpClientError(_("Requested course not found. Check `course_id` url encoding."))
    except HttpClientError as exc:
        raise HttpClientError(_("Not valid query: {}").format(exc.message))

    return all_blocks


def get_available_courses(request, source_ids=None):
    """
    Fetch all available courses from all sources of from source with provided ID.

    :param request: Request object
    :param source_ids: content provider's ID or list of the IDs
    :return: (list) course_ids
    """
    content_sources = get_active_content_sources(request, source_ids, not_allow_empty_source_id=False)

    all_courses = []
    errors = defaultdict(list)
    for content_source in content_sources:
        # Get API client instance:
        try:
            api = api_client_factory(content_source=content_source)
            all_courses.extend(
                apply_data_filter(
                    api.get_provider_courses(),
                    filters=['id', 'course_id', 'name', 'org', 'content_source_id'],
                    content_source_id=content_source.id
                )
            )
        except HttpClientError as exc:
            errors[str(exc)].append(content_source.name)

    # Convert defaultdict to dict, because django template doesn't work with defaultdict
    return all_courses, dict(errors)


def add_to_dict(data, **kwargs):
    """Add key and value to dict only if this pair not exist yet in data dict."""
    for k, v in kwargs.items():
        if k not in data:
            data[k] = v
    return data


def apply_data_filter(data, filters=None, **kwargs):
    """
    Filter for `blocks` OpenEdx Course API response.

    Picks data which is listed in `filters` only.
    :param data: (list)
    :param filters: list of desired resource keys
    :param kwargs: params to append to every object if it's not present in the object yet
    :return: list of resources which keys were filtered
    """
    if filters is None:
        return data

    filtered_data = []
    for resource in data:
        filtered_resource = {k: v for k, v in resource.items() if k in filters}
        filtered_data.append(add_to_dict(filtered_resource, **kwargs))
    return filtered_data


def get_content_providers(request, source_ids=None):
    """
    Pick active (enabled) content Sources (aka Providers).

    LTI Providers which expose courses content blocks to use in adaptive collections.
    :param request: Request object
    :param source_ids: LtiContentSource ID or list of the LtiContentSource ID or None
    :return: content_sources queryset
    """
    q_kw = {
        'is_active': True,
        'available_in_groups__in': list(request.user.groups.all()),
    }
    if source_ids:
        if isinstance(source_ids, list):
            q_kw['id__in'] = source_ids
        else:
            q_kw['id'] = source_ids
    content_source = LtiContentSource.objects.filter(**q_kw)
    log.debug('Picked content Source(s){}: {}'.format(
        " with content_source_id={}".format(source_ids),
        ", ".join(content_source.values_list('name', flat=True))))
    return content_source
