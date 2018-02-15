import logging

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseBadRequest, HttpResponseNotFound, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets
from slumber.exceptions import HttpClientError

from api.backends.openedx import get_available_blocks
from api.serializers import ActivitySerializer, CollectionSerializer
from module.models import Activity, Collection

log = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def sources(request):
    """
    Content Source backend endpoint.

    Uses OpenEdx Course API v.1.0
    :param request:
    :param course_id:
    :return: (JSON) blocks
    """
    course_id = request.POST.get('course_id')
    if not course_id:
        return HttpResponseBadRequest(reason={"error": "`course_id` is a mandatory parameter."})

    log.debug('course_ID{}'.format(course_id))

    try:
        sources_list = get_available_blocks(course_id)
    except ObjectDoesNotExist as exc:
        return HttpResponseBadRequest(reason={"error": exc.message})
    except HttpClientError as exc:
        return HttpResponseNotFound(reason={"error": exc.message})

    return JsonResponse(data=sources_list, safe=False)


class ActivityViewSet(viewsets.ModelViewSet):
    """
    Activity API view set.

    Allow programmatically create, read, update, and delete activities.
    """
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer


class CollectionViewSet(viewsets.ModelViewSet):
    """
    Collection API view set.

    Allow programmatically create, read, update, and delete collections.
    """
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
