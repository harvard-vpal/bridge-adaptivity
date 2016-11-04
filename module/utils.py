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


def get_next_missing_prereq(user_module, activity):
    '''
    Check if a activity has a prereq activity not present in sequence. If so, return first prereq activity
    '''
    sequence_activities = [item.activity for item in user_module.sequence()]
    for prereq_activity in activity.dependencies.all():
        if prereq_activity not in sequence_activities:
            return prereq_activity
    return None


def validate_sequence_history(user_module, activity):
    '''
    look for activity in sequence history, return True if not found 
    '''
    # activity ids of previously seen activities; used to check for repeated activity
    sequence_activity_ids = user_module.sequence().values_list('activity',flat=True)
    # check if activity has been seen before in sequence (excluding last item)
    if len(sequence_activity_ids)>1 and activity.pk in list(sequence_activity_ids)[:-1]:
        return False
    return True


def get_activity(user_module):
    '''
    for a given student, return the recommended next activity
    uses activity service (e.g. tutorgen api) to get next activity id, with backup logic for handling failure cases
    returns an tuple of (activity object, method), where method is a text description of method used to determine activity
    '''

	# ACTIVITY SERVICE: GET ACTIVITY
    activity_recommendation = activity_service.Activity(user_module)
    activity_id = activity_recommendation.get_activity_id()

    # backup case if request failed
    if not activity_id:
        # OPTIONAL could do another activity service request here
        activity = get_backup_activity(user_module)
        method = "backup: activity service request failed"

    activity = get_object_or_404(Activity, pk=activity_id)

    # check if activity has been seen before in sequence (excluding last item)
    if not validate_sequence_history(user_module, activity):
        activity = get_backup_activity(user_module)
        method = "backup: activity service recommended activity previously seen in sequence"

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
        method = "activity service"

    # check if activity has unfulfilled manually defined dependencies, if so replace the next activity with a prereq
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


def assign_prior_activities(user_module):
    '''
    For a given user_module, searches for previously attempted activities from the module, and associates them with the user_module
    Use case: when user first sees the module, but they have done activity from the module because they saw it in the forum, etc
    '''
    prior_attempts = Attempt.objects.filter(
        user = user_module.user,
        activity__module = user_module.module,
        activity__visible = True,
        sequence_item = None,
    )
    activity_ids = prior_attempts.values_list('activity',flat=True).distinct()
    p = user_module.sequenceitem_set.count() # should be zero if used on first load of module
    for activity_id in activity_ids:
        p += 1
        # create new sequence item
        sequence_item = SequenceItem.objects.create(
            user_module = user_module,
            position = p,
            activity_id = activity_id,
            method = "previously completed problem assigned to module"
        )
        # associate attempts with the new sequence item
        prior_attempts.filter(activity_id=activity_id).update(sequence_item=sequence_item)

    return True if prior_attempts else False
    

