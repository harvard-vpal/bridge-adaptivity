from django.http import Http404
from django.shortcuts import get_object_or_404

from module.models import Activity


def choose_activity(sequence_item=None, sequence=None):
    sequence = sequence or sequence_item.sequence

    try:
        activity_id = sequence.engine_driver.select_activity(sequence)
        return get_object_or_404(Activity, pk=activity_id)
    except (IndexError, Http404):
        sequence.completed = True
        sequence.save()
        return None
