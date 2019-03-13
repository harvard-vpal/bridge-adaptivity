from logging import getLogger

from requests.packages.urllib3.exceptions import MaxRetryError

from module.models import Activity, SequenceItem

log = getLogger(__name__)


def choose_activity(sequence_item=None, sequence=None):
    sequence = sequence or sequence_item.sequence

    try:
        engine_choose = sequence.collection_order.engine.engine_driver.select_activity(sequence)
        activity_source_launch_url = engine_choose.get('source_launch_url')
        if engine_choose.get('complete'):
            sequence.completed = True
            sequence.save()
            return
        elif activity_source_launch_url:
            return Activity.objects.filter(
                collection=sequence.collection_order.collection, source_launch_url=activity_source_launch_url
            ).first()
    except (AttributeError, MaxRetryError):
        log.exception("[Engine] Cannot get activity from the engine")

    # If all checks passed and sequence_item is not set. We are on the step sequence is created but activity is
    # not chosen - sequence is deleting for the consistency. See bridge_adaptivity.bridge_lti.provider
    if not sequence_item:
        sequence.delete()


def select_next_sequence_item(sequence_item, update_activity, last_item, position):
    """
    Chose next sequence item for the Adaptivity Demo flow.

    :param sequence_item: the instance of the current SequenceItem.
    :param update_activity: boolean flag, shows that sequence item should be updated.
    :param last_item: integer position of the last item in the sequence.
    :param position: integer position of the next sequence item.
    :return: next_sequence_item (instance of the SequenceItem), sequence_complete (boolean flag), stub (boolean flag)
    """
    sequence_complete, stub = None, None

    next_sequence_item = SequenceItem.objects.filter(
        sequence=sequence_item.sequence,
        position=position
    ).first()

    log.debug("Picked next sequence item is: {}".format(next_sequence_item))

    if not next_sequence_item or next_sequence_item.position == last_item:
        activity = choose_activity(sequence_item)
        if next_sequence_item is None:
            sequence = sequence_item.sequence
            policy = sequence.collection_order.grading_policy.policy_instance(sequence=sequence)
            policy.send_grade()
            if not activity:
                if sequence.completed:
                    return sequence_item, True, None
                return None, None, True

            next_sequence_item = SequenceItem.objects.create(
                sequence=sequence_item.sequence,
                activity=activity,
                position=sequence_item.position + 1
            )
            last_item += 1
        elif update_activity:
            log.debug('Bridge updates activity in the un-submitted SequenceItem')
            if activity:
                next_sequence_item.activity = activity
                next_sequence_item.save()
    return next_sequence_item, sequence_complete, stub
