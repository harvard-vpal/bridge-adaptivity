from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.conf import settings
from .models import *
import random
from . import utils
from django.core.exceptions import ObjectDoesNotExist
from time import sleep
from django.db import transaction


def launch(request, user_module_id):
    '''
    LTI launch redirects here when module window is initially loaded a page
    Determines which item to show and goes to correct activity in sequence
    Use cases
        student sees module for first time
        students may navigate away in the middle of the module and they come back
    '''
    user_module_id = int(user_module_id)
    user_module = get_object_or_404(UserModule, pk=user_module_id)
    sequence = user_module.sequence()
    
    # existing activity history: go to the last activity
    if sequence.exists():
        # OPTIONAL: could change this to be the last activity visited
        # go to end of sequence
        last_position = sequence.last().position

    # check for and add existing completed activities that could be added to the module
    elif utils.assign_prior_activities(user_module):
        # still go to first item if they exist
        return redirect('module:sequence_item', user_module_id=user_module_id, position=1)

    # first time someone sees the module or any problems from it
    else:
        activity = utils.get_first_activity(user_module)
        last_position = 1
        sequence_item = SequenceItem(
            user_module = user_module,
            position = 1,
            activity = activity,
            method = "default first activity"
        )
        sequence_item.save()

    return redirect('module:sequence_item', user_module_id=user_module_id, position=last_position)
    

def next_activity(request, user_module_id, position):
    '''
    Called when student clicks the "next" button - 
    Go to next item if student has already been there, or request one if not reached yet
    position argument is the position from the previous sequence item
    '''

    user_module_id = int(user_module_id)
    position = int(position)
    user_module = get_object_or_404(UserModule, pk=user_module_id)
    sequence = user_module.sequence()
    sequence_length = sequence.count()
    last_sequence_item = sequence.get(position=position)
    last_activity = last_sequence_item.activity

    # if at the most recent item in sequence, ask for a new activity
    if position == sequence_length:

        # if user doesn't have any attempts for any problem, assume that javascript isn't working for them and serve a next question
        if not Attempt.objects.filter(user=user_module.user, manual=False).exists():
            next_activity = utils.get_backup_activity(user_module=user_module)
            method = 'assumed javascript not working, served random activity'

        # if javascript seems to work, and user hasn't made any attempts for a problem, stay on the same sequence item
        elif last_activity.type=='problem' and not Attempt.objects.filter(sequence_item=last_sequence_item).exists():
            return redirect('module:sequence_item', user_module_id=user_module_id, position=position)

        # check if student has exhausted all servable questions in module; if so, go to completion screen
        elif sequence.filter(activity__type='problem').count() == Activity.objects.filter(module=user_module.module,visible=True).count():
            return redirect('module:sequence_complete', user_module_id=user_module_id)

        else:
            # ACTIVITY REQUEST: returns a tuple of (activity object, description)
            next_activity, method = utils.get_activity(user_module=user_module)

        # if activity service returns same activity as the last one, redirect to last sequence item 
        if next_activity == last_activity:
            return redirect('module:sequence_item', user_module_id=user_module_id, position=position)

        # if utils.get_activity() retuns None, this signals that the student completed the module
        if not next_activity:
            return redirect('module:sequence_complete', user_module_id=user_module_id)

        # create the next sequence item with chosen activity
        next_sequence_item = SequenceItem.objects.create(
            user_module = user_module,
            position = position + 1,
            activity = next_activity,
            method = method,
        )

    # go to the next sequence item screen
    return redirect('module:sequence_item', user_module_id=user_module_id, position=position+1)
   

def sequence_item(request, user_module_id, position):
    '''
    Activity in a module. sequence item already has to exist
    '''
    position = int(position)
    user_module_id = int(user_module_id)
    user_module = get_object_or_404(UserModule, pk=user_module_id)
    
    sequence = user_module.sequence()
    sequence_item = sequence.get(position=position)

    # update grade to display and do grade passback
    user_module.recompute_grade()
    user_module.grade_passback()

    context = {
        'user_module':user_module,
        'sequence':sequence,
        'sequence_item':sequence_item,
        'position':position,
        'sequence_length':len(sequence), # precompute sequence length for template
        'module_complete':False, # helper conditional variable for template appearance
    }

    return render(request, 'module/module.html', context) 


def sequence_complete(request, user_module_id):
    '''
    Outer view once module is complete
    '''
    user_module_id = int(user_module_id)
    user_module = get_object_or_404(UserModule, pk=user_module_id)

    # set "completion" state to true on user_module
    user_module.completed = True
    user_module.save()

    sequence = user_module.sequence()

    # update grade to display and do grade passback
    user_module.recompute_grade()
    user_module.grade_passback()

    context = {
        'user_module':user_module,
        'sequence':sequence,
        'position': len(sequence)+1,
        'sequence_length':len(sequence), # precompute sequence length for template
        'module_complete': True, # helper conditional variable for template appearance
    }

    return render(request, 'module/module.html', context)


def completion_message(request):
    '''
    replacement for activity content in sequence_complete view
    '''
    return render(request, 'module/completion_message.html')

