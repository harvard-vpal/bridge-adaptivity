# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-09 20:37
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bridge_lti', '0003_ltisource_activity'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ltisource',
            name='activity',
        ),
    ]