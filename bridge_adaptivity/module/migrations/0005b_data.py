"""
Second of three data migrations to replace 0005_auto_20180925_2041, to migrate over existing collection groups

This migration transfers colllection group membership data to the new through model.
"""

from django.db import migrations


def data_migration(apps, schema_editor):
    CollectionGroup = apps.get_model('module','CollectionGroup')
    CollectionOrder = apps.get_model('module','CollectionOrder')
    # data for through model doesn't seem to be available via parent model in migration context so load model directly and filter for data
    CollectionGroup_collections_old = apps.get_model('module','CollectionGroup_collections_old')

    # migrate data from private through model (available under collections_old) to explicit through model

    # handle one collection group at a time
    for collection_group in CollectionGroup.objects.all():
        collectiongroup_members = CollectionGroup_collections_old.objects.filter(collectiongroup=collection_group)

        for i, collectiongroup_member in enumerate(collectiongroup_members):
            # create through model instance for new collection field
            collection_order = CollectionOrder.objects.create(
                group = collection_group,
                collection = collectiongroup_member.collection,
                order = i+1  # positive integer since PositiveIntegerField is used
            )
            print(f'Created: {collection_order}')


def reverse_migration(apps, schema_editor):
    CollectionOrder = apps.get_model('module', 'CollectionOrder')
    CollectionOrder.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('module', '0005a_data'),
    ]

    operations = [
        migrations.RunPython(data_migration, reverse_code=reverse_migration)
    ]
