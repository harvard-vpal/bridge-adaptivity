"""
Third of three data migrations to replace 0005_auto_20180925_2041, to migrate over existing collection groups

This migration removes the old collections field (renamed to collections_old) from the collectiongroup model,
since it is replaced with a new one in 0005a_data, and populated with data in 0005b_data
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('module', '0005b_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='collectiongroup',
            name='collections_old',
        )
    ]
