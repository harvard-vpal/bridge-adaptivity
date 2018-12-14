"""
Data migration (3 of 3) to replace 0006_auto_20181001_0936.py
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('module', '0006b_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gradingpolicy',
            name='threshold',
        )
    ]
