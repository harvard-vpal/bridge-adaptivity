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
        return self.content_source.host_url

    def get_course_blocks(self, course_id, all_blocks=True, depth='all', type_filter=None):
        """
        Return list of the blocks for given course.

        Result list item has next structure: {block_id, display_name, lti_url, type}
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
        Return list of the courses.

        Result list item has next structure: {course_id, name, org}
        """
        resource = self.courses.get(
            username=username,
            org=org,
            mobile=mobile,
            page_size=1000,
        )
        return resource.get('results')
