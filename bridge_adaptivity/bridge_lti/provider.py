import logging

from django.core.cache import cache
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from lti import InvalidLTIRequestError
from lti.contrib.django import DjangoToolProvider
from oauthlib import oauth1

from bridge_lti.models import LtiProvider, LtiUser, OutcomeService
from bridge_lti.validator import SignatureValidator
from module import utils as module_utils
from module.models import Collection, CollectionGroup, Engine, Sequence, SequenceItem

log = logging.getLogger(__name__)


def _error_msg(s):
    return "LTI: provided wrong consumer {}.".format(s)


def find_last_sequence_item(sequence, strict_forward):
    sequence_items = sequence.items.all()
    if strict_forward and sequence_items.count() > 1:
        sequence_items = sequence_items.filter(score__isnull=False)
    return sequence_items.last()


@csrf_exempt
def lti_launch(request, collection_id=None, group_slug=''):
    """
    Endpoint for all requests to embed edX content via the LTI protocol.

    An LTI launch is successful if:
    - The launch contains all the required parameters
    - The launch data is correctly signed using a known client key/secret pair
    """
    request_post = request.POST
    try:
        tool_provider = DjangoToolProvider.from_django_request(request=request)
        validator = SignatureValidator()
        ok = tool_provider.is_valid_request(validator)
    except (oauth1.OAuth1Error, InvalidLTIRequestError, ValueError) as err:
        ok = False
        log.error('Error happened while LTI request: {}'.format(err.__str__()))
    if not ok:
        raise Http404('LTI request is not valid')
    request.session['Lti_session'] = request_post['oauth_nonce']
    lti_consumer = LtiProvider.objects.get(consumer_key=request_post['oauth_consumer_key'])
    roles = request_post.get('roles')
    # NOTE(wowkalucky): LTI roles `Instructor`, `Administrator` are considered as BridgeInstructor
    if roles and set(roles.split(",")).intersection(['Instructor', 'Administrator']):
        return instructor_flow(request, collection_id=collection_id)

    # NOTE(wowkalucky): other LTI roles are considered as BridgeLearner
    else:
        return learner_flow(
            request, lti_consumer, tool_provider, collection_id=collection_id, group_slug=group_slug
        )


def instructor_flow(request, collection_id=None):
    """Define logic flow for Instructor."""
    if not collection_id or not Collection.objects.filter(owner=request.user, id=collection_id):
        return redirect(reverse('module:collection-list'))

    return redirect(reverse('module:collection-detail', kwargs={'pk': collection_id}))


def get_collection_collectiongroup_engine(collection_id, group_slug):
    """Return collection and collection group by collection_id and group_slug."""
    collection = Collection.objects.filter(id=collection_id).first()
    if not collection:
        log.exception("Collection with provided ID does not exist. Check configured launch url.")
        raise Http404('Bad launch_url collection ID.')

    collection_group = CollectionGroup.objects.filter(slug=group_slug).first()

    if collection_group is None:
        raise Http404(
            'The launch URL is not correctly configured. The group with the slug `{}` cannot be found.'
            .format(group_slug)
        )

    if collection not in collection_group.collections.all():
        raise Http404(
            'The launch URL is not correctly configured. Collection with the ID `{}` is not in group with slug `{}`'
            .format(collection_id, group_slug)
        )

    if collection_group:
        engine = collection_group.engine or Engine.get_default()
    else:
        engine = Engine.get_default()

    return collection, collection_group, engine


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


def learner_flow(request, lti_consumer, tool_provider, collection_id=None, group_slug=None):
    """Define logic flow for Learner."""
    anononcement_page = render(
        request,
        template_name="bridge_lti/announcement.html",
        context={
            'title': 'announcement',
            'message': 'coming soon!',
            'tip': 'this adaptivity sequence is about to start.',
        }
    )
    if not collection_id:
        return anononcement_page

    collection, collection_group, engine = get_collection_collectiongroup_engine(collection_id, group_slug)

    lti_user, created = LtiUser.objects.get_or_create(
        user_id=request.POST['user_id'],
        lti_consumer=lti_consumer,
        defaults={'course_id': request.POST['context_id']}
    )
    log.debug("LTI user {}: user_id='{}'".format('created' if created else 'picked', lti_user.user_id))

    sequence_kw = dict(
        lti_user=lti_user,
        collection=collection,
        group=collection_group,
    )

    sequence, created = Sequence.objects.get_or_create(**sequence_kw)

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
            log.warn('Instructor configured empty Collection.')
            return anononcement_page
        sequence_item = create_sequence_item(
            request, sequence, start_activity, tool_provider, lti_consumer
        )
    else:
        sequence_item = find_last_sequence_item(sequence, strict_forward)
    sequence_item_id = sequence_item.id if sequence_item else None
    if not sequence_item_id:
        return redirect(reverse('module:sequence-complete', kwargs={'pk': sequence.id}))

    return redirect(reverse('module:sequence-item', kwargs={'pk': sequence_item_id}))
