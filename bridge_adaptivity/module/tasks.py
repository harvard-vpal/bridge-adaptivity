from __future__ import absolute_import, unicode_literals

from celery.task import task


@task()
def sync_collection_engines(collection_id=None, created_at=None):
    from module.models import Collection
    collection = Collection.objects.filter(id=collection_id, updated_at=created_at).first()
    if not collection:
        return
    for coll_group in collection.collection_groups.all().prefetch_related('engine'):
        # NOTE(idegtiarov) Refactor send one sync request instead of bunch of requests
        coll_group.engine.engine_driver.sync_collection_activities(collection)
