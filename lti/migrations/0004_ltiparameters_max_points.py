# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-10-12 00:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lti', '0003_auto_20160922_1654'),
    ]

    operations = [
        migrations.AddField(
            model_name='ltiparameters',
            name='max_points',
            field=models.FloatField(null=True),
        ),
    ]
