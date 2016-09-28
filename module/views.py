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
    sequence = user_module.sequenceitem_set.order_by('position')
    
    # existing activity history: go to the last activity
    if sequence.exists():
        # go to end of sequence
        last_position = sequence.last().position

     # first time someone comes to the page
    else:
        activity = utils.get_first_activity(user_module)
        last_position = 1
        sequence_item = SequenceItem(
            user_module = user_module,
            position = 1,
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


def next_activity(request, user_module_id, position):
    '''
    Called when student clicks the "next" button - 
    Go to next item if student has already been there, or request one if not reached yet
    position argument is the position from the previous sequence item
    '''

    user_module_id = int(user_module_id)
    position = int(position)
    user_module = get_object_or_404(UserModule, pk=user_module_id)
    sequence_length = user_module.sequenceitem_set.count()
    last_sequence_item = get_object_or_404(SequenceItem, user_module=user_module, position=position)
    last_activity = last_sequence_item.activity

    # if user hasn't made any attempts, stay on the same sequence item
    if not Attempt.objects.filter(activity=last_activity).exists():
        return redirect('module:sequence_item', user_module_id=user_module_id, position=position)

    # check if student has exhausted all questions in module; if so, go to completion screen
    if sequence_length == Activity.objects.filter(module=user_module.module).count():
        return redirect('module:sequence_complete', user_module_id=user_module_id)

    # if not at end of sequence, get the next item in pre-populated sequence
    if position < sequence_length:
        next_sequence_item = SequenceItem.objects.get(
            user_module = user_module,
            position = position + 1,
        )

    # if at the end of sequence, ask for a new activity
    elif position == sequence_length:

        # request activity
        next_activity = utils.get_activity(user_module=user_module)

        # if activity service returns same activity as the last one, redirect to last sequence item 
        if next_activity == last_activity:
            return redirect('module:sequence_item', user_module_id=user_module_id, position=position)

        # if utils.activity() retuns None, this signals that the student completed the module
        if not next_activity:
            return redirect('module:sequence_complete', user_module_id=user_module_id)

        try:
            # look for a next item just in case next_question is triggered more than once before page load, so the later process gets rather than creates a duplicate
            next_sequence_item = SequenceItem.objects.get(
                user_module = user_module,
                position = position + 1,
            )
        except ObjectDoesNotExist:
            next_sequence_item = SequenceItem.objects.create(
                user_module = user_module,
                position = position + 1,
                activity = next_activity,
            )

    # go to the next sequence item screen
    return redirect('module:sequence_item', user_module_id=user_module_id, position=position+1)
    

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
