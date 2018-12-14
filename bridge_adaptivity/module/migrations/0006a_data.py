"""
Data migration (1 of 3) to replace 0006_auto_20181001_0936.py
"""

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('module', '0005_auto_20180925_2041'),
    ]

    operations = [
        migrations.AddField(
            model_name='gradingpolicy',
            name='params',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default={}, help_text='Policy parameters in json format.'),
        ),
    ]
