from logging import getLogger

from celery.task import task


log = getLogger(__name__)


@task()
def sync_collection_engines(collection_slug=None, created_at=None):
    from module.models import Collection
    collection = Collection.objects.filter(slug=collection_slug, updated_at=created_at).first()
    if not collection:
        return
    for coll_group in collection.collection_groups.all().select_related('engine'):
        coll_group.engine.engine_driver.sync_collection_activities(collection)


@task()
def update_students_grades(group_id=None):
    from module.models import CollectionGroup
    group = CollectionGroup.objects.get(id=group_id)
    for sequence in group.sequence_set.all():
        if sequence.lis_result_sourcedid:
            group.grading_policy.policy_instance(sequence=sequence).send_grade()
            log.debug(f"Grade update is sent for the user {sequence.lti_user}")
