import logging

from django.core.cache import cache
from django.http import HttpResponseBadRequest, Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from lti import InvalidLTIRequestError
from lti.contrib.django import DjangoToolProvider
from oauthlib import oauth1

from bridge_lti.models import LtiProvider, LtiUser
from bridge_lti.outcomes import store_outcome_parameters
from bridge_lti.validator import SignatureValidator
from module.models import (Collection, Sequence, SequenceItem)
from module import utils as module_utils

log = logging.getLogger(__name__)


def _error_msg(s):
    return "LTI: provided wrong consumer {}.".format(s)


@csrf_exempt
def lti_launch(request, collection_id=None):
    """
    Endpoint for all requests to embed edX content via the LTI protocol.

    An LTI launch is successful if:
    - The launch contains all the required parameters
    - The launch data is correctly signed using a known client key/secret pair
    """
    request.session.clear()
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
    # NOTE(wowkalucky): LTI roles `Instructor`, `Administrator` are considered as BridgeInstructor
    lti_consumer = LtiProvider.objects.get(consumer_key=request_post['oauth_consumer_key'])
    roles = request_post.get('roles')
    if roles and set(roles.split(",")).intersection(['Instructor', 'Administrator']):
        return instructor_flow(collection_id=collection_id)

    # NOTE(wowkalucky): other LTI roles are considered as BridgeLearner
    else:
        return learner_flow(request, lti_consumer, collection_id=collection_id)


def instructor_flow(collection_id=None):
    """
    Define logic flow for Instructor.
    """
    if not collection_id:
        return redirect(reverse('module:collection-list'))

    return redirect(reverse('module:collection-detail', kwargs={'pk': collection_id}))


def learner_flow(request, lti_consumer, collection_id=None):
    """
    Define logic flow for Learner.
    """
    if not collection_id:
        return render(
            request,
            template_name="bridge_lti/announcement.html",
            context={
                'title': 'announcement',
                'message': 'coming soon!',
                'tip': 'this adaptivity sequence is about to start.',
            }
        )

    try:
        collection = Collection.objects.get(id=collection_id)
    except Collection.DoesNotExist:
        log.exception("Collection with provided ID does not exist. Check configured launch url.")
        return HttpResponseBadRequest(reason='Bad launch_url collection ID.')

    lti_user, created = LtiUser.objects.get_or_create(
        user_id=request.POST['user_id'],
        lti_consumer=lti_consumer,
        defaults={'course_id': request.POST['context_id']}
    )
    log.debug("LTI user {}: user_id='{}'".format('created' if created else 'picked', lti_user.user_id))

    sequence, created = Sequence.objects.get_or_create(
        lti_user=lti_user,
        collection=collection
    )

    if sequence.completed:
        return redirect(reverse('module:sequence-complete', kwargs={'pk': sequence.id}))

    request.session['Lti_sequence'] = sequence.id

    if created:
        # NOTE(wowkalucky): empty Collection validation
        log.debug("Sequence {} was created".format(sequence))
        start_activity = module_utils.choose_activity(sequence_item=None, sequence=sequence)
        if not start_activity:
            log.warn('Instructor configured empty Collection.')
            return render(
                request,
                template_name="bridge_lti/announcement.html",
                context={
                    'title': 'announcement',
                    'message': 'coming soon!',
                    'tip': 'this adaptivity sequence is about to start.',
                }
            )
        cache.set(str(sequence.id), request.session['Lti_session'])
        # NOTE(wowkalucky): save outcome service parameters when Sequence is created
        store_outcome_parameters(request.POST, sequence, lti_consumer)
        sequence_item = SequenceItem.objects.create(
            sequence=sequence,
            activity=start_activity,
            position=1
        )
    else:
        sequence_item = sequence.items.filter(score__isnull=False).last()

    sequence_item_id = sequence_item.id if sequence_item else None
    if not sequence_item_id:
        return redirect(reverse('module:sequence-complete', kwargs={'pk': sequence.id}))

    return redirect(reverse('module:sequence-item', kwargs={'pk': sequence_item_id}))
