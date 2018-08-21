# Generated by Django 2.0.5 on 2018-08-20 15:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_auto_20180720_0909'),
    ]

    operations = [
        migrations.AlterField(
            model_name='oauthclient',
            name='grant_type',
            field=models.CharField(blank=True, choices=[('code', 'authorization code'), ('credentials', 'client credentials')], default='credentials', help_text='OAuth grant type which is used by Client API.', max_length=255, null=True),
        ),
    ]
