import logging
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from bridge_lti.outcomes import store_outcome_parameters
from bridge_lti.validator import SignatureValidator
from module.models import (Collection, Sequence, SequenceItem)
from .models import LtiProvider, LtiUser
from .utils import get_required_params, get_optional_params

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
    # FIXME(idegtiarov) improve lti_launch with using lti library
    params = get_required_params(request.POST)
    if not params:
        return HttpResponseBadRequest()
    params.update(get_optional_params(request.POST))
    log.debug('Got LTI params: {}'.format(params))
    try:
        lti_consumer = LtiProvider.objects.get(consumer_key=params['oauth_consumer_key'])
    except LtiProvider.DoesNotExist:
        # NOTE(wowkalucky): wrong 'consumer_key':
        log.exception(_error_msg('key'))
        return render(
            request,
            template_name="bridge_lti/announcement.html",
            context={
                'title': 'forbidden',
                'message': 'please, check provided LTI credentials.',
                'tip': 'have a look at `consumer key`',
            }
        )
    if not SignatureValidator(lti_consumer).verify(request):
        # NOTE(wowkalucky): wrong 'consumer_secret':
        log.warn(_error_msg('secret'))
        return render(
            request,
            template_name="bridge_lti/announcement.html",
            context={
                'title': 'forbidden',
                'message': 'please, check provided LTI credentials.',
                'tip': 'have a look at `consumer secret`',
            }
        )
    # NOTE(wowkalucky): LTI roles `Instructor`, `Administrator` are considered as BridgeInstructor
    if params.get('roles') and set(params['roles'].split(",")).intersection(['Instructor', 'Administrator']):
        return instructor_flow(request, collection_id=collection_id)

    # NOTE(wowkalucky): other LTI roles are considered as BridgeLearner
    else:
        return learner_flow(request, lti_consumer, params, collection_id=collection_id)


def instructor_flow(_request, collection_id=None):
    """
    Define logic flow for Instructor.
    """
    if not collection_id:
        return redirect(reverse('module:collection-list'))

    return redirect(reverse('module:collection-detail', kwargs={'pk': collection_id}))


def learner_flow(request, lti_consumer, params, collection_id=None):
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
        user_id=params['user_id'],
        lti_consumer=lti_consumer,
        defaults={'course_id': params['context_id']}
    )
    log.debug("LTI user {}: user_id='{}'".format('created' if created else 'picked', lti_user.user_id))

    sequence, created = Sequence.objects.get_or_create(
        lti_user=lti_user,
        collection=collection
    )

    if sequence.completed:
        return redirect(reverse('module:sequence-complete', kwargs={'pk': sequence.id}))

    if created:
        # NOTE(wowkalucky): empty Collection validation
        start_activity = collection.activity_set.first()
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
        # NOTE(wowkalucky): save outcome service parameters when Sequence is created
        store_outcome_parameters(params, sequence, lti_consumer)
        sequence_item = SequenceItem.objects.create(
            sequence=sequence,
            activity=start_activity,
            position=1
        )
    else:
        sequence_item = sequence.sequenceitem_set.last()

    return redirect(reverse('module:sequence-item', kwargs={'pk': sequence_item.id}))
