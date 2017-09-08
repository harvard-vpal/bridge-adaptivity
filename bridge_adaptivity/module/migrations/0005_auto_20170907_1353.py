# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-09-07 13:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('module', '0004_auto_20170907_0940'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sequence',
            name='total_points',
        ),
        migrations.AddField(
            model_name='sequenceitem',
            name='points',
            field=models.FloatField(blank=True, default=0, help_text=b"Grade policy: 'p' (problem's current score)."),
        ),
    ]
