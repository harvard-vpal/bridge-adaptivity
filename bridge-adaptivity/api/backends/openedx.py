import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from edx_rest_api_client.client import EdxRestApiClient

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
        "get_token": "/oauth2/access_token/",
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

        access_token, expires_at = super(OpenEdxApiClient, self).get_oauth_access_token(
            url=url,
            client_id=settings.API_OAUTH_CLIENT_ID,
            client_secret=settings.API_OAUTH_CLIENT_SECRET,
            token_type='jwt',
        )
        return access_token, expires_at

    def get_course_blocks(self, course_id,  all_blocks=True, depth='all', type_filter=None):
        """
        Provide API GET request to OpenEdx Course Blocks endpoint.

        Optional block type filtering available.
        API query parameters:
        - block_types_filter=['sequential', 'vertical', 'html', 'problem', 'video', 'discussion']
        - block_counts=['video', 'problem'...]
        see: http://edx.readthedocs.io/projects/edx-platform-api/en/latest/courses/blocks.html#query-parameters

        :return: (dict)
        """
        resource = self.blocks.get(
            course_id=course_id,
            all_blocks=all_blocks,
            depth=depth,
            requested_fields='lti_url',
            return_type='dict',
            block_types_filter=type_filter or []
        )
        blocks = resource.get('blocks')
        return blocks


