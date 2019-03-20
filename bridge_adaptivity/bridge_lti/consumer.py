import logging
import urllib.parse

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from lti import ToolConfig, ToolConsumer

from api.backends.api_client import get_content_providers
from module.models import SequenceItem

log = logging.getLogger(__name__)


def tool_config(request):
    app_title = 'Bridge'
    app_description = 'Bridge for Adaptivity'
    launch_view_name = 'lti_launch'
    launch_url = request.build_absolute_uri(reverse(launch_view_name))

    extensions = {}

    lti_tool_config = ToolConfig(
        title=app_title,
        launch_url=launch_url,
        secure_launch_url=launch_url,
        extensions=extensions,
        description=app_description
    )

    return HttpResponse(lti_tool_config.to_xml(), content_type='text/xml')


def create_lti_launch_params(request, sequence_item_id, consumer_prams):
    """
    Construct lti launch parameters to get Activity from the Source.

    :param request: request
    :param sequence_item_id: id of the sequence_item
    :param consumer_prams: default consumer params
    :return: source_name, source_lti_url, updated consumer_prams
    """
    if sequence_item_id:
        # student flow
        sequence_item = SequenceItem.objects.get(id=sequence_item_id)
        activity = sequence_item.activity

        content_provider = activity.lti_content_source
        consumer_prams['consumer_key'] = content_provider.provider_key
        consumer_prams['consumer_secret'] = content_provider.provider_secret

        source_name = activity.source_name
        source_lti_url = activity.source_launch_url
        lis_outcome_service_url = urllib.parse.urljoin(settings.BRIDGE_HOST, reverse('module:sequence-item-grade'))
        consumer_prams['params'].update({
            'user_id': sequence_item.user_id_for_consumer,
            'context_id': sequence_item.sequence.collection_order.collection.name,
            'resource_link_id': sequence_item.id,
            # Grading required parameters:
            'lis_result_sourcedid': '{sequence_item_id}:{user_id}:{activity}:{suffix}'.format(
                sequence_item_id=sequence_item.id,
                user_id=sequence_item.sequence.lti_user.user_id,
                activity=sequence_item.activity.id,
                suffix=sequence_item.suffix,
            ),
            'lis_outcome_service_url': lis_outcome_service_url,
        })
    else:
        source_name = request.GET.get('source_name')
        source_lti_url = request.GET.get('source_lti_url')
        if source_lti_url is not None:
            # NOTE(wowkalucky): Django converts plus sign to space
            source_lti_url = request.GET.get('source_lti_url').replace(' ', '+')
    return source_name, source_lti_url, consumer_prams


def source_preview(request):
    """View to render Source content block shared through LTI."""
    log.debug("Got request.GET: %s", request.GET)

    content_source_id = request.GET.get('content_source_id')
    # pass source_id to get only on content source

    consumer_prams = {
        'consumer_key': '',
        'consumer_secret': '',
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

    # Default impersonal consumer parameters are used for getting problem's preview from the Source via LTI
    sequence_item_id = request.GET.get('sequence_item_id')
    if content_source_id:
        # staff flow
        content_provider = get_content_providers(request, content_source_id).first()

        if not content_provider:
            return render(request, 'bridge_lti/stub.html')

        consumer_prams['consumer_key'] = content_provider.provider_key
        consumer_prams['consumer_secret'] = content_provider.provider_secret

    source_name, source_lti_url, consumer_prams = create_lti_launch_params(request, sequence_item_id, consumer_prams)

    consumer_prams.update({'launch_url': source_lti_url})
    log.debug("Sending parameters are: {}".format(consumer_prams))
    consumer = ToolConsumer(**consumer_prams)
    return render(request, 'bridge_lti/content-source.html', {
        'launch_data': consumer.generate_launch_data(),
        'launch_url': consumer.launch_url,
        'source_name': source_name,
    })
