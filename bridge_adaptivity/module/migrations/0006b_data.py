"""
Data migration (2 of 3) to replace 0006_auto_20181001_0936.py
Populate new GradingPolicy.param field with previous data from GradingPolicy.threshold field (to be removed)
"""

from django.db import migrations


def data_migration(apps, schema_editor):
    GradingPolicy = apps.get_model('module', 'GradingPolicy')
    for grading_policy in GradingPolicy.objects.all():
        if grading_policy.name in ['points_earned', 'trials_count']:
            grading_policy.params = {'threshold':grading_policy.threshold}
            grading_policy.save()


def reverse_migration(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('module', '0006a_data'),
    ]

    operations = [
        migrations.RunPython(data_migration, reverse_code=reverse_migration)
    ]
