# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2018-02-07 14:09
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def forward_function(apps, schema):
    Sequence = apps.get_model("module", 'Sequence')
    Collection = apps.get_model("module", 'Collection')

    cursor = schema.connection.cursor()
    cursor.execute('select * from module_sequence;')

    items = dictfetchall(cursor)
    for item in items:
        collection = Collection.objects.get(id=item['collection_id'])
        groups = collection.collection_groups.filter(
            grading_policy_id=item['grading_policy_id'],
            engine_id=item['engine_id']
        )
        if groups.count() > 1:
            print """Could not define exact group for sequence with id={id}, will get first one...
            You will be able to change it later in Django admim UI by this URL:
            {server}/admin/module/sequence/{id}
            """.format(id=item['id'], server=settings.BRIDGE_HOST)
        group = groups.first()
        Sequence.objects.filter(id=item['id']).update(group=group)


def backward_function(apps, schema):
    Sequence = apps.get_model("module", 'Sequence')

    for item in Sequence.objects.all():
        if item.group:
            item.grading_policy_id = item.group.grading_policy_id
            item.engine_id = item.group.engine_id
            item.save()


class Migration(migrations.Migration):

    dependencies = [
        ('bridge_lti', '0001_initial'),
        ('module', '0008_auto_20180202_1716'),
    ]

    operations = [
        migrations.AddField(
            model_name='sequence',
            name='group',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='module.CollectionGroup'),
        ),
        migrations.AlterField(
            model_name='activity',
            name='stype',
            field=models.CharField(blank=True, help_text=b'(problem, video, html, etc.)', max_length=25, null=True, verbose_name=b'Type of the activity'),
        ),
        migrations.AlterUniqueTogether(
            name='sequence',
            unique_together=set([('lis_result_sourcedid', 'outcome_service'), ('lti_user', 'collection', 'group')]),
        ),
        migrations.RunPython(forward_function, backward_function),
        migrations.RemoveField(
            model_name='sequence',
            name='engine'
        ),
        migrations.RemoveField(
            model_name='sequence',
            name='grading_policy'
        ),
    ]
