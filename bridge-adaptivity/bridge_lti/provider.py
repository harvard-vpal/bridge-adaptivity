from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse

from .models import LtiProvider
from .utils import get_required_params, get_optional_params


def lti_launch(request):
    """
    Endpoint for all requests to embed edX content via the LTI protocol.

    An LTI launch is successful if:
    - The launch contains all the required parameters
    - The launch data is correctly signed using a known client key/secret pair
    """
    params = get_required_params(request.POST)
    if not params:
        return HttpResponseBadRequest()

    try:
        lti_provider = LtiProvider.objects.get(consumer_key=params['oauth_consumer_key'])
    except LtiProvider.DoesNotExist:
        return HttpResponseForbidden()

    params.update(get_optional_params(request.POST))

    # TODO: Check the OAuth signature on the message.
    # TODO: Add the course and usage keys to the parameters array.
    # TODO: Create an Bridge LtiUser if the user identified by the LTI launch doesn't have one already.
    # TODO: Create an BridgeUser if the user identified by the LTI launch as Instructor and doesn't have one already.

    return redirect(reverse('index'))
