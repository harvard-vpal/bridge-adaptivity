from module.models import *
from django.shortcuts import get_object_or_404
import random
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from time import sleep
from django.conf import settings
from django.db.models import Sum

## choose the recommendation service here
if settings.ACTIVITY_SERVICE is 'tutorgen':
    import tutorgen_api as activity_service
else:
    import activity_service.utils as activity_service
    

def get_first_activity(user_module):
    activity = Activity.objects.filter(module=user_module.module).first()
    return activity

def get_backup_activity(user_module):
    '''
    hopefully don't use this
    get a random activity from the remaining questions left in the module
    '''
    previous_activity_ids = list(user_module.sequenceitem_set.values_list('activity',flat=True))
    activity = Activity.objects.filter(module=user_module.module,visible=True).exclude(pk__in=previous_activity_ids).first()
    return activity


def retry_get_activity(user_module, last_activity_id=None):
    '''
    # maybe transaction hasn't updated the system yet and the same activity as the last one is returned
    # in this case retry after a 2 second wait

    '''
    user = user_module.user

    NUM_RETRIES = 1 # number of extra retries in case returned activity id is same as last activity
    TIME_BETWEEN_RETRIES = 2 # time in seconds between retries

    if activity_id == last_activity_id:
        # number of extra retries
        retries = NUM_RETRIES
        while retries > 0:
            sleep(TIME_BETWEEN_RETRIES)
            activity_id = activity_service.get_activity_id(
                user = user,
                module = module,
            )
            retries -= 1


def get_next_missing_prereq(user_module, activity):
    '''
    Check if a activity has a prereq activity not present in sequence. If so, return first prereq activity
    '''
    sequence = user_module.sequenceitem_set
    for prereq_activity in activity.dependencies.all():
        if prereq_activity not in sequence:
            return prereq_activity
    return None


def get_activity(user_module):
    '''
    for a given student, return the recommended next activity
    uses activity service (e.g. tutorgen api) to get next activity id, with backup logic for handling failure cases
    returns an tuple of (activity object, method), where method is a text description of method used to determine activity
    '''

    user = user_module.user

	# get activity from tutorgen
    activity_recommendation = activity_service.Activity(user_module)
    activity_id = activity_recommendation.get_activity_id()

    # backup case if request failed
    if not activity_id:
        activity = get_backup_activity(user_module)
        method = "backup: activity service request failed"

    # module completion
    elif activity_recommendation.level_up():
        # double check if student has seen enough questions in sequence to reach max_points of module
        if user_module.validate_max_points():
            return None, None
        # if condition not satisfied, serve a backup question instead
        else:
            activity = get_backup_activity(user_module)
            method = "backup: insufficient max_points sequence total"

    else:
        activity = get_object_or_404(Activity, pk=activity_id)
        method = "activity service"

    # check if activity has unfulfilled manually defined dependencies
    prereq_activity = get_next_missing_prereq(user_module, activity)
    if prereq_activity:
        return prereq_activity, "prerequisite"

    return activity, method


def get_random_activity(**kwargs):
    '''
    demo function for simulating activity selection
    '''
    N = len(Activity.objects.all())
    activity_id = random.randint(1,N)
    return activity_id


def assign_prior_attempts(user_module,sequence_item):
    '''
    # # check if there are prior attempts for the chosen next activity (in case they see through forums and user/sequence_item fields didn't get set)
    # # in that case, associate the attempts with this sequence item / user
    sequence item should already have somethign assigned to it
    '''
    prior_attempts = Attempt.objects.filter(
        username=user_module.ltiparameters.lis_person_sourcedid,
        activity=sequence_item.activity,
        user = None,
        sequence_item = None
    ).update(
        user = user_module.user,
        sequence_item = sequence_item,
    )

def assign_prior_activities(user_module):
    '''
    For a given user_module, searches for previously attempted activities from the module, and associates them with the user_module
    Use case: when user first sees the module, but they have done activity from the module because they saw it in the forum, etc
    '''
    prior_attempts = Attempt.objects.filter(
        user = user_module.user,
        activity__module = user_module.module,
        sequence_item = None,
    )
    activity_ids = prior_attempts.values_list('activity',flat=True).distinct()
    p = user_module.sequenceitem_set.count() # should be zero if used on first load of module
    for activity_id in activity_ids:
        p += 1
        # create new sequence item
        SequenceItem.objects.create(
            user_module = user_module,
            activity_id = activity_id,
            position = p
        )
        # associate attempts with the new sequence item
        prior_attempts.filter(activity_id=activity_id).update(sequence_item=sequence_item)

    return True if prior_attempts else False
    

