from django.http import JsonResponse
from module.models import *
from module import utils
from lti.utils import grade_passback
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
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
    print "[problem_attempt]: problem attempt API submission recieved"
    # identify problem based on usage id
    try: 
        activity = Activity.objects.get(usage_id = request.POST['problem'])
    except ObjectDoesNotExist:
        return JsonResponse({
            'success':False,
            'message': 'problem not found for given usage id'
        })

    print "[problem_attempt]: getting or creating user"
    # get or create the user by the edx username
    username = request.POST.get('user','')
    if not username:
        return JsonResponse({
            'success':False,
            'message': 'username not given',
        })
    user, created = User.objects.get_or_create(username=request.POST['user'])
    
    print "[problem_attempt]: creating or saving attempt"
    # create and save the attempt
    attempt = Attempt.objects.create(
        activity = activity,
        user = user,
        points = float(request.POST['points']),
        # max_points may not be passed if question is ungraded, in which case it is set to 0
        max_points = float(request.POST.get('max_points', 0)), 
    )

    print "[problem_attempt]: sending transaction to activity service"
    # ACTIVITY SERVICE: TRANSACTION
    # submit problem grade info to activity service
    transaction = activity_service.Transaction(attempt)

    # everything below this point is only relevant for problems that could be served in adaptive modules
    if not activity.visible:
        return JsonResponse({
            'success': True,
            'message': 'attempt recorded, non-adaptive problem'
        })

    print "[problem_attempt]: identifying user module"
    # try to identify a user module for the activity
    try:
        user_module = UserModule.objects.get(user=user,module=activity.module)
    # if user_module doesn't exist, user hasn't seen the activity yet
    except ObjectDoesNotExist:
        return JsonResponse({
            'success':True,
            'message': 'attempt recorded, outside of adaptive module context',
        })

    print "[problem_attempt]: identifying sequence_item"
    # if user_module found, try to find a sequence item within module
    try:
        sequence_item = user_module.sequenceitem_set.get(activity=activity)
    # if activity could have been served in user_module but not served yet, add to user_module
    except ObjectDoesNotExist:
        sequence_length = user_module.sequenceitem_set.count()
        sequence_item = SequenceItem.objects.create(
            user_module = user_module,
            activity = activity,
            position = sequence_length+1,
        )
    # shouldn't be true, but just in case there are duplicate activities in sequence
    except MultipleObjectsReturned:
        sequence_item = SequenceItem.objects.filter(user=user,activity=activity).last()
        print "WARNING: Multiple sequence items returned for user={} and activity={}".format(user, activity)

    # at this point, both user_module and sequence item are identified
    
    # update the attempt object with the sequence item
    attempt.sequence_item = sequence_item
    attempt.save(update_fields=['sequence_item'])

    print "[problem_attempt]: recomputing grade"
    # recompute user_module.grade state and do grade passback
    user_module.recompute_grade()
    print "[problem_attempt]: doing grade passback"
    user_module.grade_passback()
    print "[problem_attempt]: grade passback completed"
    return JsonResponse({
        'success':True,
        'message':'attempt recorded and module grade updated',
    })

