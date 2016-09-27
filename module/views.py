from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.conf import settings
from .models import *
import random
from . import utils
from django.core.exceptions import ObjectDoesNotExist
from time import sleep


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
    sequence = user_module.sequenceitem_set.order_by('position')
    
    # existing activity history: go to the last activity
    if sequence.exists():
        # go to end of sequence
        last_position = sequence.last().position

        # alternative: go to last activity visited
        # last_position = sequence.get(position=user_module.last_position)

     # first time someone comes to the page
    else:
        activity = utils.get_first_activity(user_module)
        last_position = 1
        sequence_item = SequenceItem(
            user_module=user_module,
            position=1,
            activity = activity,
        )
        sequence_item.save()

    return redirect('module:sequence_item', user_module_id=user_module_id, position=last_position)
    

def sequence_item(request, user_module_id, position):
    '''
    Activity in a module. sequence item already has to exist
    '''
    position = int(position)
    user_module_id = int(user_module_id)
    user_module = get_object_or_404(UserModule, pk=user_module_id)
    
    sequence = user_module.sequenceitem_set.order_by('position')
    sequence_item = sequence.get(position=position)

    # # check if there are prior attempts for the chosen next activity (in case they see through forums and user/sequence_item fields didn't get set)
    # # in that case, associate the attempts with this sequence item / user
    utils.assign_prior_attempts(user_module, sequence_item)

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

    sequence = user_module.sequenceitem_set.order_by('position')
    # sequence_item = sequence.get(position=position)

    # update grade to display and do grade passback
    user_module.recompute_grade()
    user_module.grade_passback()

    # dictionary replacement for sequence_item

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


def next_activity(request, user_module_id, position):
    '''
    Called when student clicks the "next" button - 
    Go to next item if student has already been there, or request one if not reached yet
    position argument is the position from the previous sequence item
    '''

    # pause, to increase the chance that previous attempt submission have made it into the database
    # sleep(.1)

    user_module_id = int(user_module_id)
    position = int(position)
    user_module = get_object_or_404(UserModule, pk=user_module_id)

    # if user hasn't made any attempts, don't move them to the next question; just reload the same one without making new sequence item
    last_activity = None
    if position > 0:
        last_sequence_item = get_object_or_404(SequenceItem, user_module=user_module, position=position)
        last_activity = last_sequence_item.activity
        if not Attempt.objects.filter(sequence_item=last_sequence_item).exists():
            return redirect('module:sequence_item', user_module_id=user_module_id, position=position)

    # check if student has exhausted all questions in module; if so, go to completion screen
    if user_module.sequenceitem_set.count() == Activity.objects.filter(module=user_module.module).count():
        return redirect('module:sequence_complete', user_module_id=user_module_id)

    # get the next item in sequence, or create if needed
    # not using django get_or_create shortcut here because we may not want to save the created instance
    try:
        next_sequence_item = SequenceItem.objects.get(
            user_module = user_module,
            position = position+1,
        )
        exists = True

    except ObjectDoesNotExist:
        next_sequence_item = SequenceItem(
            user_module = user_module,
            position = position+1,
        )
        exists = False

    # if created just now, make an api call to get a new activity
    if not exists:

        # ask for next activity
        next_activity = utils.get_activity(
            user_module = user_module,
            # last_activity_id = last_activity_id,
        )

        ## in these two cases the next sequence_item is NOT saved

        # 1. if same activity, redirect to same 
        if next_activity == last_activity:
            return redirect('module:sequence_item', user_module_id=user_module_id, position=position)

        # 2. if next_activity = None here, this signals that the student completed the module
        if not next_activity:
            return redirect('module:sequence_complete', user_module_id=user_module_id)

        # Go ahead and save the proposed next sequence_item with the recommended activity
        next_sequence_item.activity = next_activity
        next_sequence_item.save()


    return redirect('module:sequence_item', user_module_id=user_module_id, position=position+1)
    


