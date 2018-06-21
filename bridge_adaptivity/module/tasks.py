

from celery.task import task


@task()
def sync_collection_engines(collection_slug=None, created_at=None):
    from module.models import Collection
    collection = Collection.objects.filter(slug=collection_slug, updated_at=created_at).first()
    if not collection:
        return
    for coll_group in collection.collection_groups.all().select_related('engine'):
        coll_group.engine.engine_driver.sync_collection_activities(collection)
