# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-10-12 04:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('module', '0003_auto_20161012_0016'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='visible',
            field=models.BooleanField(default=False),
        ),
    ]
