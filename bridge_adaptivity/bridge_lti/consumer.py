import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from lti import ToolConfig, ToolConsumer

from api.backends.openedx import get_content_provider
from module.models import Activity

log = logging.getLogger(__name__)


def tool_config(request):
    app_title = 'Bridge'
    app_description = 'Bridge for Adaptivity'
    launch_view_name = 'lti_launch'  # noqa: F841
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


@login_required
def source_preview(request):
    """
    Simple view to render Source content block shared through LTI.
    """
    log.debug("Got request.POST: %s", request.POST)
    log.debug("Got request.GET: %s", request.GET)

    activity_id = request.GET.get('activity_id')
    if activity_id:
        activity = Activity.objects.get(id=activity_id)
        source_name = activity.source_name
        source_lti_url = activity.source_launch_url
    else:
        source_name = request.GET.get('source_name')
        source_lti_url = request.GET.get('source_lti_url')
        if source_lti_url is not None:
            # NOTE(wowkalucky): Django converts plus sign to space
            source_lti_url = request.GET.get('source_lti_url').replace(u' ', u'+')

    content_provider = get_content_provider()
    if not content_provider:
        return render(request, 'bridge_lti/stub.html')

    initial_lti_user_id = request.session['lti:user_id']
    initial_lti_context_id = request.session['lti:context_id']
    initial_lis_result_sourcedid = request.session['lti:lis_result_sourcedid']

    consumer = ToolConsumer(
        consumer_key=content_provider.provider_key,
        consumer_secret=content_provider.provider_secret,
        launch_url=source_lti_url,
        params={
            # NOTE(wowkalucky): required params
            'roles': 'Student, Learner',
            'context_id': initial_lti_context_id,
            'user_id': initial_lti_user_id,
            'resource_link_id': initial_lis_result_sourcedid,
            # NOTE(wowkalucky): outcome params
            'lis_outcome_service_url': 'bridge-outcome-service-url-here',  # FIXME(wowkalucky): specify real URL
            'lis_result_sourcedid': initial_lis_result_sourcedid,

            'lti_version': 'LTI - 1p0',
            'lti_message_type': 'basic-lti-launch-request',
            'oauth_callback': 'about:blank',
        }
    )
    log.debug('Sent LTI params: {}'.format(consumer.to_params()))
    return render(request, 'bridge_lti/content-source.html', {
        'launch_data': consumer.generate_launch_data(),
        'launch_url': consumer.launch_url,
        'source_name': source_name,
    })
