import logging
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from bridge_lti.validator import SignatureValidator
from module.models import (Collection, Sequence, SequenceItem)
from .models import LtiProvider, LtiUser
from .utils import get_required_params, get_optional_params

log = logging.getLogger(__name__)


@csrf_exempt
def lti_launch(request, collection_id=None):
    """
    Endpoint for all requests to embed edX content via the LTI protocol.

    An LTI launch is successful if:
    - The launch contains all the required parameters
    - The launch data is correctly signed using a known client key/secret pair
    """
    params = get_required_params(request.POST)
    if not params:
        return HttpResponseBadRequest()
    params.update(get_optional_params(request.POST))

    try:
        lti_consumer = LtiProvider.objects.get(consumer_key=params['oauth_consumer_key'])
    except LtiProvider.DoesNotExist:
        # wrong 'consumer_key':
        log.exception('LTI: provided wrong consumer key.')
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
        # wrong 'consumer_secret':
        log.warn('LTI: provided wrong consumer secret.')
        return render(
            request,
            template_name="bridge_lti/announcement.html",
            context={
                'title': 'forbidden',
                'message': 'please, check provided LTI credentials.',
                'tip': 'have a look at `consumer secret`',
            }
        )

    if params['roles'] in ['Student', 'Learner']:
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
            return HttpResponseBadRequest()

        lti_user, created = LtiUser.objects.get_or_create(
            user_id=params['user_id'],
            lti_consumer=lti_consumer,
            defaults={'course_id': params['context_id']}
        )
        sequence, created = Sequence.objects.get_or_create(
            lti_user=lti_user,
            collection=collection
        )

        if sequence.completed:
            return redirect(reverse('module:sequence-complete', kwargs={'pk': sequence.id}))

        if created:
            sequence_item = SequenceItem.objects.create(
                sequence=sequence,
                activity=collection.activity_set.first(),
                position=1
            )
        else:
            sequence_item = sequence.sequenceitem_set.last()

        return redirect(reverse('module:sequence-item', kwargs={'pk': sequence_item.id}))

    else:
        return redirect(reverse('module:collection-list'))
