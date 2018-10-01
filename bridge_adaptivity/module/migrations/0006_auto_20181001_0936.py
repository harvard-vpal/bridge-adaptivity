# Generated by Django 2.0.5 on 2018-10-01 09:36

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('module', '0005_auto_20180925_2041'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gradingpolicy',
            name='threshold',
        ),
        migrations.AddField(
            model_name='gradingpolicy',
            name='params',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default={}, help_text='Policy parameters in json format.'),
        ),
    ]
