from logging import getLogger

from requests.packages.urllib3.exceptions import MaxRetryError

from module.models import Activity

log = getLogger(__name__)


def choose_activity(sequence_item=None, sequence=None):
    sequence = sequence or sequence_item.sequence

    try:
        engine_choose = sequence.group.engine.engine_driver.select_activity(sequence)
        activity_source_launch_url = engine_choose.get('source_launch_url')
        if engine_choose.get('complete'):
            sequence.completed = True
            sequence.save()
            return
        elif activity_source_launch_url:
            return Activity.objects.filter(
                collection=sequence.collection, source_launch_url=activity_source_launch_url
            ).first()
    except (AttributeError, MaxRetryError):
        log.exception("[Engine] Cannot get activity from the engine")

    # If all checks passed and sequence_item is not set. We are on the step sequence is created but activity is
    # not chosen - sequence is deleting for the consistency. See bridge_adaptivity.bridge_lti.provider
    if not sequence_item:
        sequence.delete()
