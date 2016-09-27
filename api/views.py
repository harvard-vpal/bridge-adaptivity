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

    # construct initial attempt object
    attempt = Attempt(
        activity = activity,
        username = request.POST['user'],
        points = float(request.POST['points']),
        max_points = float(request.POST.get('points', 0)), # max_points may not be passed for some questions
    )
    attempt.save()

    # identify user by looking for user_module, based on edx username and activity.module
    # if seen before we will have an associated user module
    try: 
        print "getting user module that corresponds to username {} and module {}".format(request.POST['user'],activity.module.pk)
        user_module = UserModule.objects.get(
            ltiparameters__lis_person_sourcedid = request.POST['user'],
            module = activity.module,
        )
        # set user object on attempt.user
        attempt.user = user_module.user

    # if there is no existing user module, still save attempt instance but take no further action (like posting to tutorgen)
    except ObjectDoesNotExist:
        print 'attempt recorded but user, activity.module combo not found'
        attempt.save()
        return JsonResponse({
            'success':True,
            'message': 'attempt recorded, but (user, activity.module) combination not recognized',
        })

    # submit problem grade info to tutorgen
    transaction = activity_service.Transaction(attempt)

    # identify the sequence_item for the activity
    try:
        print "identifying sequence item for activity"
        attempt.sequence_item = user_module.sequenceitem_set.get(activity=activity)
        attempt.save()
    # what if student is doing problem outside the lti module, before they get to the activity in the module
    except ObjectDoesNotExist:
        attempt.save()
        return JsonResponse({
            'success':True,
            'message': 'attempt recorded but sequence_item not identifiable',
        })

    # recompute user_module.grade state and do grade passback
    print "recomputing grade, doing grade passback"
    user_module.recompute_grade()
    user_module.grade_passback()

    return JsonResponse({
        'success':True,
        'message':'Grade submitted successfully',
    })

