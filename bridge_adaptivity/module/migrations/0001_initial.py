# Generated by Django 2.1.7 on 2019-03-19 09:21

import common.mixins.models
from django.conf import settings
import django.contrib.postgres.fields.jsonb
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import multiselectfield.db.fields
import slugger.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bridge_lti', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(db_index=True, editable=False)),
                ('name', models.CharField(max_length=255)),
                ('tags', models.CharField(blank=True, help_text='Provide your tags separated by a comma.', max_length=255, null=True)),
                ('atype', models.CharField(choices=[('G', 'generic'), ('A', 'pre-assessment'), ('Z', 'post-assessment')], default='G', help_text="Choose 'pre/post-assessment' activity type to pin Activity to the start or the end of the Collection.", max_length=1, verbose_name='type')),
                ('difficulty', models.FloatField(default='0.5', help_text='Provide float number in the range 0.0 - 1.0', validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1.0)])),
                ('points', models.FloatField(blank=True, default=1)),
                ('source_launch_url', models.URLField(max_length=255, null=True)),
                ('source_name', models.CharField(blank=True, max_length=255, null=True)),
                ('stype', models.CharField(blank=True, help_text='(problem, video, html, etc.)', max_length=25, null=True, verbose_name='Type of the activity')),
                ('repetition', models.PositiveIntegerField(default=1, help_text='The number of possible repetition of the Activity in the sequence.')),
            ],
            options={
                'verbose_name_plural': 'Activities',
                'ordering': ('atype', 'order'),
            },
        ),
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('slug', slugger.fields.AutoSlugField(help_text='Add the slug for the collection. If field empty slug will be created automatically.', populate_from='name', unique=True, verbose_name='slug id')),
                ('metadata', models.CharField(blank=True, max_length=255, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='CollectionOrder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(db_index=True, editable=False)),
                ('slug', models.SlugField(default=uuid.uuid4, unique=True)),
                ('strict_forward', models.BooleanField(default=True)),
                ('ui_option', multiselectfield.db.fields.MultiSelectField(blank=True, choices=[('AT', 'Questions viewed/total'), ('EP', 'Earned grade'), ('RW', 'Answers right/wrong')], help_text='Add an optional UI block to the student view', max_length=8)),
                ('ui_next', models.BooleanField(default=False, help_text='Add an optional NEXT button under the embedded unit.')),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='module.Collection')),
            ],
            options={
                'ordering': ('group', 'order'),
            },
            bases=(common.mixins.models.HasLinkedSequenceMixin, models.Model),
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('slug', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Engine',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('engine', models.CharField(choices=[('engine_mock', 'mock'), ('engine_vpal', 'vpal')], default='engine_mock', max_length=100)),
                ('engine_name', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('host', models.URLField(blank=True, null=True)),
                ('token', models.CharField(blank=True, max_length=255, null=True)),
                ('lti_parameters', models.TextField(blank=True, default='', help_text='LTI parameters to sent to the engine, use comma separated string')),
                ('is_default', models.BooleanField(default=False, help_text='If checked Engine will be used as the default!')),
            ],
            bases=(common.mixins.models.ModelFieldIsDefaultMixin, models.Model),
        ),
        migrations.CreateModel(
            name='GradingPolicy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20)),
                ('public_name', models.CharField(max_length=255)),
                ('params', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default={}, help_text='Policy parameters in json format.')),
                ('is_default', models.BooleanField(default=False)),
                ('engine', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='module.Engine')),
            ],
            bases=(common.mixins.models.ModelFieldIsDefaultMixin, models.Model),
        ),
        migrations.CreateModel(
            name='Log',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True, null=True)),
                ('log_type', models.CharField(choices=[('O', 'Opened'), ('S', 'Submitted'), ('A', 'Admin')], max_length=32)),
                ('answer', models.BooleanField(default=False, verbose_name='Is answer correct?')),
                ('attempt', models.PositiveIntegerField(default=0)),
                ('action', models.CharField(blank=True, choices=[('AC', 'Activity created'), ('AU', 'Activity updated'), ('AD', 'Activity deleted'), ('CC', 'Collection created'), ('CU', 'Collection updated')], max_length=2, null=True)),
                ('data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default={})),
            ],
        ),
        migrations.CreateModel(
            name='ModuleGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('atime', models.DateTimeField(auto_now_add=True)),
                ('slug', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('collections', models.ManyToManyField(blank=True, related_name='collection_groups', through='module.CollectionOrder', to='module.Collection')),
                ('course', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='course_groups', to='module.Course')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Sequence',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('completed', models.BooleanField(default=False)),
                ('lis_result_sourcedid', models.CharField(max_length=255, null=True)),
                ('metadata', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default={})),
                ('suffix', models.CharField(default='', max_length=15)),
                ('collection_order', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='module.CollectionOrder')),
                ('lti_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bridge_lti.LtiUser')),
                ('outcome_service', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='bridge_lti.OutcomeService')),
            ],
        ),
        migrations.CreateModel(
            name='SequenceItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveIntegerField(default=1)),
                ('score', models.FloatField(blank=True, help_text="Grade policy: 'p' (problem's current score).", null=True)),
                ('suffix', models.CharField(default='', max_length=10)),
                ('is_problem', models.BooleanField(default=True)),
                ('activity', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='module.Activity')),
                ('sequence', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='items', to='module.Sequence')),
            ],
            options={
                'verbose_name': 'Sequence Item',
                'verbose_name_plural': 'Sequence Items',
                'ordering': ['sequence', 'position'],
            },
        ),
        migrations.AddField(
            model_name='log',
            name='sequence_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='module.SequenceItem'),
        ),
        migrations.AlterUniqueTogether(
            name='engine',
            unique_together={('host', 'token')},
        ),
        migrations.AddField(
            model_name='collectionorder',
            name='engine',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='module.Engine'),
        ),
        migrations.AddField(
            model_name='collectionorder',
            name='grading_policy',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='module.GradingPolicy'),
        ),
        migrations.AddField(
            model_name='collectionorder',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='module.ModuleGroup'),
        ),
        migrations.AddField(
            model_name='activity',
            name='collection',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='activities', to='module.Collection'),
        ),
        migrations.AddField(
            model_name='activity',
            name='lti_content_source',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='bridge_lti.LtiContentSource'),
        ),
        migrations.AlterUniqueTogether(
            name='sequence',
            unique_together={('lti_user', 'collection_order', 'suffix')},
        ),
        migrations.AlterUniqueTogether(
            name='collection',
            unique_together={('owner', 'name')},
        ),
        migrations.AlterUniqueTogether(
            name='activity',
            unique_together={('source_launch_url', 'collection')},
        ),
    ]
