import urllib
import urlparse

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from lti import ToolConfig, ToolConsumer

from api.backends.openedx import get_content_provider
from module.models import Activity, SequenceItem


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


# @login_required
def source_preview(request):
    """
    Simple view to render Source content block shared through LTI.
    """
    content_provider = get_content_provider()
    if not content_provider:
        return render(request, 'bridge_lti/stub.html')
    consumer_prams = {
        'consumer_key': content_provider.provider_key,
        'consumer_secret': content_provider.provider_secret,
        'params': {
            # Required parameters
            'lti_message_type': 'basic-lti-launch-request',
            'lti_version': 'LTI-1p0',
            'resource_link_id': 'reaource_link_id',
            # Recommended parameters
            'user_id': 'bridge_user',
            'roles': 'Learner',
            'oauth_callback': 'about:blank',
            'context_id': 'bridge_collection'
        },
    }
    import logging; log = logging.getLogger(__name__)
    # Default impersonal consumer parameters are used for getting problem's preview from the Source via LTI
    sequence_item_id = request.GET.get('sequence_item_id')
    if sequence_item_id:
        sequence_item = SequenceItem.objects.get(id=sequence_item_id)
        activity = sequence_item.activity
        source_name = activity.source_name
        source_lti_url = activity.source_launch_url
        lis_outcome_service_url = urlparse.urljoin(settings.BRIDGE_HOST, reverse('module:sequence-item-grade'))
        consumer_prams['params'].update({
            'user_id': sequence_item.sequence.lti_user,
            'context_id': sequence_item.sequence.collection.name,
            'resource_link_id': sequence_item.id,
            # Grading required parameters:
            'lis_result_sourcedid': '{sequence_item_id}:{user_id}'.format(
                sequence_item_id=sequence_item.id, user_id=sequence_item.sequence.lti_user.user_id
            ),
            'lis_outcome_service_url': lis_outcome_service_url,
        })
        log.warning("Sequence Item is found lis_outcome_service_url is {}/tUser_id is {}".format(lis_outcome_service_url, sequence_item.sequence.lti_user))
    else:
        source_name = request.GET.get('source_name')
        source_lti_url = request.GET.get('source_lti_url')
        if source_lti_url is not None:
            # NOTE(wowkalucky): Django converts plus sign to space
            source_lti_url = request.GET.get('source_lti_url').replace(u' ', u'+')
    consumer_prams.update({'launch_url': source_lti_url})
    log.debug("Sending parameters are: {}".format(consumer_prams))

    consumer = ToolConsumer(**consumer_prams)
    return render(request, 'bridge_lti/content-source.html', {
        'launch_data': consumer.generate_launch_data(),
        'launch_url': consumer.launch_url,
        'source_name': source_name,
    })
