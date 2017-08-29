from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from lti import ToolConfig, ToolConsumer

from api.backends.openedx import get_content_provider
from module.models import Activity


def tool_config(request):
    app_title = 'Bridge'
    app_description = 'Bridge for Adaptivity'
    launch_view_name = 'lti_launch'
    launch_url = request.build_absolute_uri(reverse('lti_launch'))

    extensions = {}

    lti_tool_config = ToolConfig(
        title=app_title,
        launch_url=launch_url,
        secure_launch_url=launch_url,
        extensions=extensions,
        description=app_description
    )

    return HttpResponse(lti_tool_config.to_xml(), content_type='text/xml')


def source_preview(request):
    """
    Simple view to render Source content block shared through LTI.
    """
    activity_id = request.GET.get('activity_id')
    if activity_id:
        activity = Activity.objects.get(id=activity_id)
        source_name = activity.source_name
        source_lti_url = activity.source_launch_url
    else:
        source_name = request.GET.get('source_name')
        source_lti_url = request.GET.get('source_lti_url')
        if source_lti_url is not None:
            # Django converts plus sign to space
            source_lti_url = request.GET.get('source_lti_url').replace(u' ', u'+')

    content_provider = get_content_provider()
    if not content_provider:
        return render(request, 'bridge_lti/stub.html')

    consumer = ToolConsumer(
        consumer_key=content_provider.provider_key,
        consumer_secret=content_provider.provider_secret,
        launch_url=source_lti_url,

        params={
            'roles': 'Instructor',  # required
            'context_id': 'bridge_collection_editor',  # required
            'user_id': 'bridge-for-adaptivity',  # required
            'resource_link_id': 'resource_id',

            'lti_version': 'LTI - 1p0',
            'lti_message_type': 'basic-lti-launch-request',
            'oauth_callback': 'about:blank',
        }
    )
    return render(request, 'bridge_lti/content-source.html', {
        'launch_data': consumer.generate_launch_data(),
        'launch_url': consumer.launch_url,
        'source_name': source_name,
    })
