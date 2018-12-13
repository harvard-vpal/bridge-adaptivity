"""
First of three data migrations to replace 0005_auto_20180925_2041, to migrate over existing collection groups

This migration updates the new collectiongroup.collections field with the through model to store order info, but first
renames the old field to collectiongroup.collections_old instead of deleting.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('module', '0004_remove_activity_source_context_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='CollectionOrder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(db_index=True, editable=False)),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='module.Collection')),
            ],
            options={
                'ordering': ('group', 'order'),
            },
        ),
        migrations.RenameField(
            model_name='collectiongroup',
            old_name='collections',
            new_name='collections_old'
        ),
        migrations.AddField(
            model_name='collectiongroup',
            name='collections',
            field=models.ManyToManyField(blank=True, related_name='collection_groups', through='module.CollectionOrder',
                                         to='module.Collection'),
        ),
        migrations.AddField(
            model_name='collectionorder',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='module.CollectionGroup'),
        ),
    ]
