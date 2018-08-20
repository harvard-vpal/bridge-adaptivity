import logging

import slumber

from api.backends.base_api_client import BaseApiClient

log = logging.getLogger(__name__)


class DartApiClient(BaseApiClient):
    """
    API client to interact with DART.
    """

    def __init__(self, content_source):
        BaseApiClient.__init__(self, content_source=content_source)
        log.debug("Creating new Dart API client...")

        # Pass to the slumber additional parameters: auth and append_slash
        slumber.API.__init__(self, self.url, auth=self.auth_request_decorator, append_slash=False)

    @property
    def auth_request_decorator(self):
        def result(request):
            request.headers['Authorization'] = 'Bearer {}'.format(self.content_source.o_auth_client.client_secret)
            return request
        return result

    @property
    def url(self):
        return f'{self.content_source.host_url}/corpus/api/v1/'

    def get_provider_courses(self):
        request = self.collections.get()
        data = request['data']
        result = [
            {
                'course_id': collection['uid'],
                'name': collection['title'],
                'org': collection['content_creator'],
            }
            for collection in data
        ]
        return result

    def get_course_blocks(self, course_id):
        request = self.collections(course_id).get()
        assets_list = request['asset_uids']
        result = []
        for asset in assets_list:
            asset_request = self.assets(asset).get()
            content_type = asset_request['asset']['content_type']
            if content_type == 'vertical':
                continue
            lti_url = None
            for data_source in asset_request['asset']['content_embed']:
                if data_source['protocol'] == 'lti':
                    lti_url = data_source['data']
                    break
            if not lti_url:
                continue
            title = asset_request['asset']['title']
            result.append({
                'block_id': asset,
                'display_name': title,
                'lti_url': lti_url,
                'type': content_type,
                'visible_to_staff_only': False,
            })
        return result
