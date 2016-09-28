from django.http import JsonResponse
from module.models import *
from module import utils
from lti.utils import grade_passback
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

## choose the recommendation service here
if settings.ACTIVITY_SERVICE is 'tutorgen':
    from module import tutorgen_api as activity_service
else:
    import activity_service.utils as activity_service


def problem_attempt(request):
    '''
    when students make a problem submission in edx, 
    embedded javascript sends the answer data to this API endpoint    
    '''
    
    # identify problem based on usage id
    try: 
        activity = Activity.objects.get(usage_id = request.POST['problem'])
    except ObjectDoesNotExist:
        return JsonResponse({
            'success':False,
            'message': 'problem not found for given usage id'
        })

    # create and save the attempt
    attempt = Attempt.objects.create(
        activity = activity,
        username = request.POST['user'],
        points = float(request.POST['points']),
        max_points = float(request.POST.get('points', 0)), # max_points may not be passed for some questions
    )

    # attempt to populate user field on attempt instance
    # identify user by looking for existing user_module, based on edx username and activity.module
    try: 
        user_module = UserModule.objects.get(
            ltiparameters__lis_person_sourcedid = request.POST['user'],
            module = activity.module,
        )
        # set user object on attempt.user
        attempt.user = user_module.user
        attempt.save()

    # if there is no existing user module, still save attempt instance but take no further action (like posting transaction to activity service)
    except ObjectDoesNotExist:
        return JsonResponse({
            'success':True,
            'message': 'attempt recorded, but user_module not identified',
        })

    # submit problem grade info to activity service
    transaction = activity_service.Transaction(attempt)

    # identify the sequence_item for the activity
    try:
        attempt.sequence_item = user_module.sequenceitem_set.get(activity=activity)
        attempt.save()

    # catches a case where student does the problem outside the lti module, before they see the activity in the module
    except ObjectDoesNotExist:
        return JsonResponse({
            'success':True,
            'message': 'attempt recorded and user_module identified, but sequence_item with specified activity not found',
        })

    # recompute user_module.grade state and do grade passback
    user_module.recompute_grade()
    user_module.grade_passback()

    return JsonResponse({
        'success':True,
        'message':'Grade submitted successfully',
    })

