# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-16 12:24
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('module', '0002_auto_20170809_2037'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='source',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='bridge_lti.LtiSource'),
        ),
    ]
