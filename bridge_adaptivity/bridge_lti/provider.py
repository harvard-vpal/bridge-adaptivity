import logging

from django.core.cache import cache
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from lti import InvalidLTIRequestError
from lti.contrib.django import DjangoToolProvider
from oauthlib import oauth1

from bridge_lti.models import LtiProvider, LtiUser, OutcomeService
from bridge_lti.validator import SignatureValidator
from common.utils import find_last_sequence_item, get_collection_collectiongroup_engine, stub_page
from module import utils as module_utils
from module.models import Collection, Sequence, SequenceItem

log = logging.getLogger(__name__)


def _error_msg(s):
    return "LTI: provided wrong consumer {}.".format(s)


def get_tool_provider_for_lti(request):
    """
    Return tool provider for the given request.

    In case of invalid lti request return None.
    """
    try:
        tool_provider = DjangoToolProvider.from_django_request(request=request)
        validator = SignatureValidator()
        if tool_provider.is_valid_request(validator):
            return tool_provider
    except (oauth1.OAuth1Error, InvalidLTIRequestError, ValueError) as err:
        log.error('Error happened while LTI request: {}'.format(err.__str__()))
    return None


@csrf_exempt
def lti_launch(request, collection_slug=None, group_slug='', unique_marker=''):
    """
    Endpoint for all requests to embed edX content via the LTI protocol.

    An LTI launch is successful if:
    - The launch contains all the required parameters
    - The launch data is correctly signed using a known client key/secret pair
    """
    request_post = request.POST
    tool_provider = get_tool_provider_for_lti(request)

    if not tool_provider:
        raise Http404('LTI request is not valid')
    request.session['Lti_session'] = request_post['oauth_nonce']
    lti_consumer = LtiProvider.objects.get(consumer_key=request_post['oauth_consumer_key'])
    roles = request_post.get('roles')
    # NOTE(wowkalucky): LTI roles `Instructor`, `Administrator` are considered as BridgeInstructor
    if roles and set(roles.split(",")).intersection(['Instructor', 'Administrator']):
        return instructor_flow(request, collection_slug=collection_slug)

    # NOTE(wowkalucky): other LTI roles are considered as BridgeLearner
    else:
        return learner_flow(
            request,
            lti_consumer,
            tool_provider,
            collection_slug=collection_slug,
            group_slug=group_slug,
            unique_marker=unique_marker
        )


def instructor_flow(request, collection_slug=None):
    """
    Define logic flow for Instructor.
    """
    if not collection_slug:
        return redirect(reverse('module:collection-list'))
    return redirect(
        reverse(
            'module:collection-detail',
            kwargs={'pk': Collection.objects.get(slug=collection_slug).id}
        )
    )


def create_sequence_item(request, sequence, start_activity, tool_provider, lti_consumer):
    """Create and return sequence item."""
    # NOTE(wowkalucky): empty Collection validation
    cache.set(str(sequence.id), request.session['Lti_session'])

    # NOTE(wowkalucky): save outcome service parameters when Sequence is created:
    if tool_provider.is_outcome_service():
        outcomes, __ = OutcomeService.objects.get_or_create(
            lis_outcome_service_url=tool_provider.launch_params.get('lis_outcome_service_url'),
            lms_lti_connection=lti_consumer
        )
        sequence.lis_result_sourcedid = tool_provider.launch_params.get('lis_result_sourcedid')
        sequence.outcome_service = outcomes
        sequence.save()

    sequence_item = SequenceItem.objects.create(
        sequence=sequence,
        activity=start_activity,
        position=1
    )
    return sequence_item


def learner_flow(request, lti_consumer, tool_provider, collection_slug=None, group_slug=None, unique_marker=''):
    """
    Define logic flow for Learner.
    """
    if not collection_slug:
        return stub_page(request)

    collection, collection_group, engine = get_collection_collectiongroup_engine(collection_slug, group_slug)

    lti_user, created = LtiUser.objects.get_or_create(
        user_id=request.POST['user_id'],
        lti_consumer=lti_consumer,
        defaults={'course_id': request.POST['context_id']}
    )
    log.debug("LTI user {}: user_id='{}'".format('created' if created else 'picked', lti_user.user_id))

    sequence, created = Sequence.objects.get_or_create(
        lti_user=lti_user,
        collection=collection,
        group=collection_group,
        suffix=unique_marker,
    )

    # Update sequence metadata with lti parameters required by the engine
    sequence.fulfil_sequence_metadata(engine.lti_params, tool_provider.launch_params)

    strict_forward = collection.strict_forward
    request.session['Lti_sequence'] = sequence.id
    request.session['Lti_strict_forward'] = strict_forward

    if sequence.completed:
        log.debug("Sequence {} is already completed".format(sequence.id))
        return redirect(reverse('module:sequence-complete', kwargs={'pk': sequence.id}))

    if created:
        log.debug("Sequence {} was created".format(sequence))
        start_activity = module_utils.choose_activity(sequence_item=None, sequence=sequence)
        if not start_activity:
            log.warning('Instructor configured empty Collection.')
            return stub_page(
                request,
                title="Warning",
                message="Cannot get the first question to start.",
                tip="Please try again later"
            )
        sequence_item = create_sequence_item(
            request, sequence, start_activity, tool_provider, lti_consumer
        )
    else:
        sequence_item = find_last_sequence_item(sequence, strict_forward)
    sequence_item_id = sequence_item.id if sequence_item else None
    if not sequence_item_id:
        return stub_page(
            request,
            title="Warning",
            message="Cannot find sequence item to start from.",
            tip="Ask help from the site admins."
        )

    return redirect(reverse('module:sequence-item', kwargs={'pk': sequence_item_id}))
