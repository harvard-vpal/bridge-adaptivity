import logging

from celery.exceptions import TimeoutError
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseBadRequest, HttpResponseNotFound, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets
from rest_framework.decorators import api_view
from slumber.exceptions import HttpClientError

from api.backends.api_client import get_available_blocks
from api.serializers import ActivitySerializer, CollectionSerializer
from module import views as module_views
from module.models import Activity, Collection

log = logging.getLogger(__name__)


def check_source_course(request):
    """
    Check that source_id and course_id parameters are present and valid.

    :param request: django request
    :return: sourceID, courseID, error (or None if no error)
    """
    error = None
    course_id = request.POST.get('course_id')
    source_id = request.POST.get('content_source_id')

    if not course_id:
        error = HttpResponseBadRequest(reason={"error": "`course_id` is a mandatory parameter."})

    if not source_id:
        error = HttpResponseBadRequest(reason={"error": "`source_id` is a mandatory parameter."})

    return source_id, course_id, error


@csrf_exempt
@require_http_methods(["POST"])
def sources(request):
    """
    Content Source backend endpoint.

    Uses OpenEdx Course API v.1.0
    :param request:
    :return: (JSON) blocks
    """
    source_id, course_id, error = check_source_course(request)

    if error:
        return error
    try:
        sources_list = get_available_blocks(request, source_id=source_id, course_id=course_id)
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

    serializer_class = ActivitySerializer
    filter_fields = ['collection', 'source_launch_url']

    def get_queryset(self):
        """
        Filter Activities owned by the user.
        """
        user = self.request.user
        return Activity.objects.filter(collection__owner=user)


class CollectionViewSet(viewsets.ModelViewSet):
    """
    Collection API view set.

    Allow programmatically create, read, update, and delete collections.
    """

    serializer_class = CollectionSerializer
    filter_fields = ['slug']

    def get_queryset(self):
        """
        Filter Collections owned by the user.
        """
        user = self.request.user
        return Collection.objects.filter(owner=user)


@api_view(['GET'])
def sync_collection(request, slug):
    """
    Sync collection - engine API.

    :param slug: collection_slug identifier.
    :return: JSON response with the sync result
        {
            "engines": [
                 {"<engine_name_1>": {"success": true}},
                 {"<engine_name_2>": {"success": false, "message": "Message of error description"}}
            ]
        }
    """
    try:
        result = [v for obj, v in module_views.sync_collection(request, slug, api_request=True)]
    except TimeoutError:
        log.debug(f"The Collection sync task failed because of timeout error.")
        return HttpResponseBadRequest(reason="Collection sync was failed, the reason is: TimeoutError")
    log.debug(f"The result of the sync task is: {result}")
    return JsonResponse(data={'engines': result})
