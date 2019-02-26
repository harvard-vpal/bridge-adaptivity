from django.utils.translation import ugettext as _
from requests.exceptions import ConnectionError
import slumber


class BaseApiClient(slumber.API):
    """
    Provide base class for the content source API.
    """

    def __init__(self, content_source):
        self.content_source = content_source
        super().__init__(self.url)

    @property
    def url(self):
        return f'{self.content_source.host_url}/api/v1/'

    def get_course_blocks(self, course_id):
        """
        Return list of the blocks for given course.

        Result list item has next structure: {block_id, display_name, lti_url, type}
        """
        resource = self.blocks.get(
            course_id=course_id,
            all_blocks=True,
            depth='all',
            requested_fields='lti_url,visible_to_staff_only',
            return_type='list'
        )
        return resource

    def get_provider_courses(self):
        """
        Return list of the courses.

        Result list item has next structure: {course_id, name, org}
        """
        try:
            resource = self.courses.get(
                username=None,
                org=None,
                mobile=None,
                page_size=1000,
            )
            return resource.get('results')
        except ConnectionError:
            raise slumber.exceptions.HttpClientError(_("Incorrect URL."))
