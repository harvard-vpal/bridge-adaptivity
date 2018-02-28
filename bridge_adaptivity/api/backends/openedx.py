from datetime import datetime
import logging

from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _
from edx_rest_api_client.client import EdxRestApiClient
from requests import RequestException
from slumber.exceptions import HttpClientError, HttpNotFoundError

from bridge_lti.models import LtiConsumer

log = logging.getLogger(__name__)


class OpenEdxApiClient(EdxRestApiClient):
    """API client to interact with OpenEdx Course API."""

    API_URLS = {
        "get_token": "/oauth2/access_token",
        "base_url": "/api/courses/v1/",
    }

    def __init__(self, content_source, url=None, jwt=None, **kwargs):
        log.debug("Creating new OpenEdx API client...")
        self.content_source = content_source

        if not url:
            url = '{}{}'.format(content_source.host_url, self.API_URLS['base_url'])
        if not jwt:
            api_client_id = self.content_source.o_auth_client.client_id
            token_cache_key = "api:{}:token".format(api_client_id)

            access_token = cache.get(token_cache_key)
            if not access_token:
                access_token, expires_at = self.get_oauth_access_token()
                ttl = expires_at - datetime.now()
                cache.set(token_cache_key, access_token, ttl.seconds)

        super(OpenEdxApiClient, self).__init__(url, jwt=access_token, **kwargs)

    def get_oauth_access_token(self):
        """
        Request OpenEdx API OAuth2 token.

        Token type: JWT (reference: https://jwt.io/).
        :return: access_token, expires_at
        """
        url = "{host_url}{token_url}".format(
            host_url=self.content_source.host_url,
            token_url=self.API_URLS['get_token']
        )
        log.debug("Requesting oauth token: (url={})".format(url))
        try:
            oauth_client = self.content_source.o_auth_client
            access_token, expires_at = super(OpenEdxApiClient, self).get_oauth_access_token(
                url=url,
                client_id=oauth_client.client_id,
                client_secret=oauth_client.client_secret,
                token_type='jwt',
            )
        except ObjectDoesNotExist:
            raise HttpClientError(
                "OAuth token request failure. Please, configure OAuth client in order to be able make API requests."
            )
        except ValueError:
            log.exception(
                "You may want to check your OAuth registration on LTI Provider."
                "LTI Provider may be disabled (to enable: LMS config > FEATURES > ENABLE_OAUTH2_PROVIDER: true"
            )
            raise HttpClientError(
                "OAuth token request failure. You may want to check your OAuth registration on LTI Provider or"
                "enable OAuth Provider."
            )
        except RequestException:
            log.exception('OAuth2 token request to the OpenEdx LTI Provider failed.')
            raise HttpClientError(
                "OAuth token request failure. You may want to check your LTI Provider's HOST_URL(https)."
            )
        return access_token, expires_at

    def get_course_blocks(self, course_id, all_blocks=True, depth='all', type_filter=None):
        """
        Provide API GET request to OpenEdx Course Blocks endpoint.

        Optional block type filtering available.
        Endpoint: /api/courses/v1/blocks/?course_id
        API query parameters:
        - block_types_filter=['sequential', 'vertical', 'html', 'problem', 'video', 'discussion']
        - block_counts=['video', 'problem'...]
        -
        see: http://edx.readthedocs.io/projects/edx-platform-api/en/latest/courses/blocks.html#query-parameters

        :param filter_function: partially applied function `apply_data_filter` with filter parameters.
        :return: (list)
        """
        resource = self.blocks.get(
            course_id=course_id,
            all_blocks=all_blocks,
            depth=depth,
            requested_fields='lti_url',
            return_type='list',
            block_types_filter=type_filter or []
        )
        return resource

    def get_provider_courses(self, username=None, org=None, mobile=None):
        """
        Provide API GET request to OpenEdx Courses Resource endpoint.

        Gets a List of Courses.
        Endpoint: /api/courses/v1/courses/
        see: http://edx.readthedocs.io/projects/edx-platform-api/en/latest/courses/courses.html#query-parameters
        :return: (dict)
        """
        resource = self.courses.get(
            username=username,
            org=org,
            mobile=mobile
        )
        return resource.get('results')


def get_active_content_sources(source_id=None, not_allow_empty_source_id=True):
    """
    Check that passed source_id parameter is valid.

    If there's only one active source provider - source_id parameter is not required, it will get first active.
    :param source_id: LtiConsumer object id
    :param not_allow_empty_source_id: if True - it will not allow empty source_id, if False - source_id could be None
    :return: queryset of content_sources
    :raise HttpClientError: if provided parameters are not valid
    """
    if not_allow_empty_source_id and not source_id:
        # if source_id is not provided and more than one active content_provider
        raise HttpClientError(_("Parameter source_id is mandatory if there's more than one active content source."))

    content_sources = get_content_providers(source_id=source_id)

    if not content_sources:
        # if no active content sources
        raise HttpClientError(_("No active Content Provider"))

    return content_sources


def get_available_blocks(source_id, course_id=''):
    """
    Content Source API requester.

    Fetches all source blocks from the course with the given ID.
    Blocks data is filtered by `apply_data_filter`.
    :param course_id: Course id
    :param source_id: LtiConsumer id
    :return: (list) blocks data
    """
    content_source = get_active_content_sources(source_id).first()
    all_blocks = []

    # Get API client instance:
    api = OpenEdxApiClient(content_source=content_source)
    try:
        # filter function will be applied to api response
        all_blocks.extend(
            apply_data_filter(
                api.get_course_blocks(
                    course_id, type_filter=['html', 'problem', 'video']
                ),
                filters=['id', 'block_id', 'display_name', 'lti_url', 'type', 'content_source_id'],
                context_id=course_id,
                content_source_id=content_source.id
            )
        )
    except HttpNotFoundError:
        raise HttpClientError(_("Requested course not found. Check `course_id` url encoding."))
    except HttpClientError as exc:
        raise HttpClientError(_("Not valid query: {}").format(exc.message))

    return all_blocks


def get_available_courses(source_id=None):
    """
    Fetch all available courses from all sources of from source with provided ID.

    :param source_id: content provider's ID
    :return: (list) course_ids
    """
    content_sources = get_active_content_sources(source_id, not_allow_empty_source_id=False)

    all_courses = []

    for content_source in content_sources:
        # Get API client instance:
        api = OpenEdxApiClient(content_source=content_source)
        try:
            all_courses.extend(
                apply_data_filter(
                    api.get_provider_courses(),
                    filters=['id', 'course_id', 'name', 'org', 'content_source_id'],
                    content_source_id=content_source.id
                )
            )
        except HttpClientError as exc:
            raise HttpClientError(_("Not valid query: {}").format(exc.message))

    return all_courses


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


def get_content_providers(source_id=None):
    """
    Pick active (enabled) content Sources (aka Providers).

    LTI Providers which expose courses content blocks to use in adaptive collections.
    :param source_id: LtiConsumer ID or None
    :return: content_sources queryset
    """
    q_kw = {
        'is_active': True
    }
    if source_id:
        q_kw['id'] = source_id
    content_source = LtiConsumer.objects.filter(**q_kw)
    log.debug('Picked content Source(s){}: {}'.format(
        " with content_source_id={}".format(source_id),
        ", ".join(content_source.values_list('name', flat=True))))
    return content_source
