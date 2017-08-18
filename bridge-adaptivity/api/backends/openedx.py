import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.utils.translation import ugettext as _
from edx_rest_api_client.client import EdxRestApiClient
from requests import RequestException
from slumber.exceptions import HttpClientError, HttpNotFoundError

from bridge_lti.models import LtiConsumer

log = logging.getLogger(__name__)

API_OAUTH_CLIENT_ID = getattr(settings, 'API_OAUTH_CLIENT_ID', None)
API_OAUTH_CLIENT_SECRET = getattr(settings, 'API_OAUTH_CLIENT_SECRET', None)
# TODO: implement OAuth client model (LtiConsumer related)?

if API_OAUTH_CLIENT_ID is None or API_OAUTH_CLIENT_SECRET is None:
    raise ImproperlyConfigured(
        "`API_OAUTH_CLIENT_ID` and `API_OAUTH_CLIENT_SECRET` should be provided in order to use Content Source API."
    )


class OpenEdxApiClient(EdxRestApiClient):
    """
    API client to interact with OpenEdx Course API.
    """
    API_URLS = {
        "get_token": "/oauth2/access_token",
        "base_url": "/api/courses/v1/",
    }

    def __init__(self, content_source, url=None, jwt=None, **kwargs):
        self.content_source = content_source
        self.access_token = jwt
        self.expires_at = None  # TODO: token caching

        if not url:
            url = '{}{}'.format(content_source.host_url, self.API_URLS['base_url'])
        if not jwt:
            self.access_token, self.expires_at = self.get_oauth_access_token()

        super(OpenEdxApiClient, self).__init__(url, jwt=self.access_token, **kwargs)

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
        try:
            access_token, expires_at = super(OpenEdxApiClient, self).get_oauth_access_token(
                url=url,
                client_id=settings.API_OAUTH_CLIENT_ID,
                client_secret=settings.API_OAUTH_CLIENT_SECRET,
                token_type='jwt',
            )
        except ValueError as exc:
            log.exception(
                'OAuth2 token request to the OpenEdx LTI Provider failed: {}'.format(exc.message)
            )
            raise HttpClientError(
                "OAuth token request failure. You may want to check your OAuth registration on LTI Provider."
            )
        except RequestException as exc:
            log.exception(
                'OAuth2 token request to the OpenEdx LTI Provider failed: {}'.format(exc.message)
            )
            raise HttpClientError(
                "OAuth token request failure. You may want to check your LTI Provider's HOST_URL(https)."
            )
        return access_token, expires_at

    def get_course_blocks(self, course_id,  all_blocks=True, depth='all', type_filter=None):
        """
        Provide API GET request to OpenEdx Course Blocks endpoint.

        Optional block type filtering available.
        Endpoint: /api/courses/v1/blocks/?course_id
        API query parameters:
        - block_types_filter=['sequential', 'vertical', 'html', 'problem', 'video', 'discussion']
        - block_counts=['video', 'problem'...]
        see: http://edx.readthedocs.io/projects/edx-platform-api/en/latest/courses/blocks.html#query-parameters

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

    def get_provider_courses(self, username=None,  org=None, mobile=None):
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


def get_available_blocks(course_id):
    """
    Content Source API requester.

    Fetches all source blocks from the course with given ID.
    Blocks data is filtered by `apply_data_filter`.
    :param course_id:
    :return: (list) blocks data
    """
    content_source = get_content_provider()

    # Get API client instance:
    api = OpenEdxApiClient(content_source=content_source)

    try:
        blocks = api.get_course_blocks(course_id)
        filtered_blocks = apply_data_filter(blocks, filters=['id', 'block_id', 'display_name', 'lti_url'])
    except HttpNotFoundError:
        raise HttpClientError(_("Requested course not found. Check `course_id` url encoding."))
    except HttpClientError:
        raise HttpClientError(_("Not valid query."))

    return filtered_blocks


def get_available_courses():
    """
    Fetch all available courses.
    :param content_provider: LtiConsumer instance
    :return: (list) course_ids
    """
    content_source = get_content_provider()

    # Get API client instance:
    api = OpenEdxApiClient(content_source=content_source)

    try:
        courses_list = api.get_provider_courses()
        filtered_courses = apply_data_filter(courses_list, filters=['id', 'course_id', 'name', 'org'])
    except HttpClientError:
        raise HttpClientError(_("Not valid query."))

    return filtered_courses


def apply_data_filter(data, filters=None):
    """
    Filter for `blocks` OpenEdx Course API response.

    Picks data which is listed in `filters` only.
    :param data: (list)
    :param filters: list of desired resource keys
    :return: list of resources which keys were filtered
    """
    if filters is None:
        return data

    filtered_data = []
    for resource in data:
        filtered_resource = {k: v for k, v in resource.items() if k in filters}
        filtered_data.append(filtered_resource)

    return filtered_data


def get_content_provider():
    """
    Pick active (enabled) content Sources (aka Providers).

    LTI Providers which expose courses content blocks to use in adaptive collections.
    :return: content_source
    """
    try:
        # TODO: multiple ContentSources processing - one, for now.
        content_source = LtiConsumer.objects.get(is_active=True)
        log.debug('Picked content Source: {}'.format(content_source.name))
        return content_source
    except LtiConsumer.DoesNotExist:
        raise ObjectDoesNotExist(_("There are no active content Sources(Providers) for now."))
