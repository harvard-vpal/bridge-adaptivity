from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from lti import ToolConfig, ToolConsumer

from api.backends.openedx import get_content_provider
from bridge_lti.models import LtiSource


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


def content_source(request, pk):
    """
    Simple view to render Source's component shared through LTI.
    """
    lti_source = LtiSource.objects.get(id=pk)
    consumer = ToolConsumer(
        consumer_key=lti_source.lti_consumer.provider_key,
        consumer_secret=lti_source.lti_consumer.provider_secret,
        launch_url=lti_source.launch_url,

        params={
            'roles': 'Student',                                 # required
            # STAGE: hardcoded values
            'context_id': 'course-v1:Harvard+VPAL-101+2017',    # required
            'user_id': 'spy1d1f8e0c19c2491fda39df7168b09',      # required
            'resource_link_id': 'resource_id',

            'lti_version': 'LTI - 1p0',
            'lti_message_type': 'basic-lti-launch-request',
            'oauth_callback': 'about:blank',
        }
    )

    return render(request, 'bridge_lti/content-source.html', {
        'launch_data': consumer.generate_launch_data(),
        'launch_url': consumer.launch_url
    })


def source_preview(request):
    source_name = request.GET.get('source_name')
    source_id = request.GET.get('source_id').replace(u' ', u'+')  # Django strips plus sign
    source_lti_url = request.GET.get('source_lti_url').replace(u' ', u'+')

    content_provider = get_content_provider()
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
        'source_id': source_id,
        'source_name': source_name,
    })
