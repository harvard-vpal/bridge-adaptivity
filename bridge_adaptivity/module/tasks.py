from logging import getLogger

from celery.task import task


log = getLogger(__name__)


@task()
def sync_collection_engines(collection_slug=None, created_at=None):
    from module.models import Collection, CollectionOrder
    collection = Collection.objects.filter(slug=collection_slug, updated_at=created_at).first()
    if not collection:
        return
    sync_result = {}
    for coll_collection_order in CollectionOrder.objects.filter(collection=collection).select_related('engine'):
        try:
            coll_collection_order.engine.engine_driver.sync_collection_activities(collection)
            result = {'success': True}
        except Exception as err:
            result = {'success': False, 'message': str(err)}
        sync_result[coll_collection_order.engine.engine_name] = result
    return sync_result


@task()
def update_students_grades(collection_order_slug=None):
    from module.models import CollectionOrder
    collection_order = CollectionOrder.objects.get(slug=collection_order_slug)
    for sequence in collection_order.sequence_set.all():
        if sequence.lis_result_sourcedid:
            collection_order.grading_policy.policy_instance(sequence=sequence).send_grade()
            log.debug(f"Grade update is sent for the user {sequence.lti_user}")
