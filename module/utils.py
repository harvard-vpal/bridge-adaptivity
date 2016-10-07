from module.models import *
from django.shortcuts import get_object_or_404
import random
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from time import sleep
from django.conf import settings

## choose the recommendation service here
if settings.ACTIVITY_SERVICE is 'tutorgen':
    import tutorgen_api as activity_service
else:
    import activity_service.utils as activity_service

# import activity_service.utils as activity_service

def get_first_activity(user_module):
    activity = Activity.objects.filter(module=user_module.module).first()
    return activity

def get_backup_activity(user_module):
    '''
    hopefully don't use this
    get a random activity from the remaining questions left in the module
    '''
    previous_activity_ids = list(user_module.sequenceitem_set.values_list('activity',flat=True))
    activity = Activity.objects.filter(module=user_module.module).exclude(pk__in=previous_activity_ids).first()
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



def get_activity(user_module):
    '''
    for a given student, return the recommended next activity
    uses tutorgen api to get next activity id
    returns an activity object instance
    has some backup logic for handling failure cases
    '''

    user = user_module.user

	# get activity from tutorgen
    # recommended_activity is a object associated with the tutorgen api, rather than a django Activity
    recommended_activity = activity_service.Activity(user_module)
    if recommended_activity.level_up():
        return None

    activity_id = recommended_activity.get_activity_id()

    # backup case
    # somehow an activity_id isn't found in here, or the request failed
    if not activity_id:
        return get_backup_activity(user_module)

    # look up activity object by id
    activity = get_object_or_404(Activity, pk=activity_id)

    return activity


def get_activity_placeholder(**kwargs):
    '''
    placeholder function for use in development
    TODO delete this if not needed anymore
    '''
    # placeholder
    return Activity.objects.get(pk=1)


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
