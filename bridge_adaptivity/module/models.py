import importlib
import logging

from autoslug import AutoSlugField
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import fields
from django.db.models.aggregates import Count, Sum
from django.urls import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from ordered_model.models import OrderedModel

from bridge_lti.models import BridgeUser, LtiConsumer, LtiUser, OutcomeService
from module import ENGINE


log = logging.getLogger(__name__)


@python_2_unicode_compatible
class Sequence(models.Model):
    """Represents User's problem solving track."""

    lti_user = models.ForeignKey(LtiUser)
    collection = models.ForeignKey('Collection')
    engine = models.ForeignKey('Engine', blank=True, null=True)
    collection_group = models.ForeignKey('CollectionGroup')
    completed = fields.BooleanField(default=False)
    lis_result_sourcedid = models.CharField(max_length=255, null=True)
    outcome_service = models.ForeignKey(OutcomeService, null=True)

    class Meta:
        unique_together = (('lti_user', 'collection'), ('lis_result_sourcedid', 'outcome_service'))

    def __str__(self):
        return '<Sequence[{}]: {}>'.format(self.id, self.lti_user)


@python_2_unicode_compatible
class SequenceItem(models.Model):
    """Represents one User's step in problem solving track."""

    sequence = models.ForeignKey('Sequence', related_name='items', null=True)
    activity = models.ForeignKey('Activity', null=True)
    position = models.PositiveIntegerField(default=1)
    score = models.FloatField(null=True, blank=True, help_text="Grade policy: 'p' (problem's current score).")

    __origin_score = None

    def __init__(self, *args, **kwargs):
        super(SequenceItem, self).__init__(*args, **kwargs)
        self.__origin_score = self.score

    class Meta:
        verbose_name = "Sequence Item"
        verbose_name_plural = "Sequence Items"
        ordering = ['sequence', 'position']

    def __str__(self):
        return u'<SequenceItem: {}={}>'.format(self.sequence, self.activity.name)

    def save(self, *args, **kwargs):
        """Extension sending notification to the Adaptive engine that score is changed."""
        if self.score != self.__origin_score:
            ENGINE.submit_activity_answer(self)
            log.debug("Adaptive engine is updated with the grade for the {} activity in the SequenceItem {}".format(
                self.activity.name, self.id
            ))
        super(SequenceItem, self).save(*args, **kwargs)


class CollectionGradingPolicy(models.Model):
    collection = models.ForeignKey('Collection')
    grading_policy = models.ForeignKey('GradingPolicy')

    threshold = models.PositiveIntegerField(blank=True, default=0, help_text="Grade policy: 'Q'")

    def _points_earned_grade(self, trials_count, points_earned):
        return points_earned / max(self.threshold, trials_count)

    def _trials_count(self, trials_count):
        return trials_count / max(self.threshold, trials_count)

    def calculate_grade(self, sequence):
        items_result = sequence.items.aggregate(points_earned=Sum('score'), trials_count=Count('score'))
        map = {
            # name, function
            'points_earned': (self._points_earned_grade, (items_result['trials_count'], items_result['points_earned'])),
            'trials_count': (self._trials_count, (items_result['trials_count'],))
        }
        if self.grading_policy.name in map:
            func = map[self.grading_policy.name][0]
            return func(*map[self.grading_policy.name][1])


class GradingPolicy(models.Model):
    """Predefined set of Grading policy objects. Define how to grade collections."""

    name = models.CharField(max_length=255)
    collections = models.ManyToManyField('Collection', through=CollectionGradingPolicy)


@python_2_unicode_compatible
class Collection(models.Model):
    """Set of Activities (problems) for a module."""

    name = fields.CharField(max_length=255)
    owner = models.ForeignKey(BridgeUser)
    # threshold = models.PositiveIntegerField(blank=True, default=0, help_text="Grade policy: 'Q'")
    metadata = fields.CharField(max_length=255, blank=True, null=True)
    strict_forward = fields.BooleanField(default=True)

    # correctness_matters = fields.BooleanField(
    #     default=True,
    #     verbose_name="Correctness matters (grading policy setting)",
    #     help_text=('If checked: grade will depend on points user get,<br>'
    #                'If unchecked: grade will depend on users trials count.')
    # )

    class Meta:
        unique_together = ('owner', 'name')

    def __str__(self):
        return u'<Collection: {}>'.format(self.name)

    def save(self, *args, **kwargs):
        """Extension cover method with logging."""
        initial_id = self.id
        super(Collection, self).save(*args, **kwargs)

        if initial_id:
            Log.objects.create(
                log_type=Log.ADMIN, action=Log.COLLECTION_UPDATED,
                data={'collection_id': self.id}
            )
        else:
            Log.objects.create(
                log_type=Log.ADMIN, action=Log.COLLECTION_CREATED,
                data={'collection_id': self.id}
            )

    def get_absolute_url(self):
        return reverse('module:collection-list')


class Engine(models.Model):
    """Defines engine settings."""

    DEFAULT_ENGINE_NAME = 'mock'

    name = models.CharField(default=DEFAULT_ENGINE_NAME, max_length=255)
    host = models.URLField(blank=True, null=True)
    token = models.CharField(max_length=255, blank=True, null=True)

    _engines_cache = {}

    class Meta:
        unique_together = ('host', 'token')

    def __str__(self):
        return "Engine: {}".format(self.name)

    @classmethod
    def get_default_engine(cls):
        return Engine.objects.get_or_create(name=cls.DEFAULT_ENGINE_NAME)

    def make_engine(self):
        if self.name == 'mock':
            # mock engine takes no params
            settings = {}
        else:
            settings = {
                'host': self.host,
                'token': self.token
            }
        key = (self.name, tuple(settings.items()))
        if key in Engine._engines_cache:
            # if engine already in cache - return it
            return Engine._engines_cache.get(key)
        # otherwise create Engine, put it in cache and return it
        engine_module = importlib.import_module('module.engines.engine_{}'.format(self.name.lower()))
        engine_template = 'Engine{}'
        driver = getattr(
            engine_module, engine_template.format(self.name.upper()),  # try uppercase
            getattr(
                engine_module,
                engine_template.format(self.name.capitalize()),  # if not found - try capitalized
            )
        )
        Engine._engines_cache[key] = driver(**settings)
        return Engine._engines_cache[key]


class CollectionGroup(models.Model):
    """Represents Collections Group."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    atime = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(BridgeUser)
    slug = AutoSlugField(
        null=True,
        populate_from='name',
        unique_with=['owner'],
    )

    collections = models.ManyToManyField(Collection)

    engine = models.ForeignKey(Engine)

    def __str__(self):
        return u"CollectionGroup: {}".format(self.name)

    def get_absolute_url(self):
        return reverse('module:group-detail', kwargs={'pk': self.pk})


@python_2_unicode_compatible
class Activity(OrderedModel):
    """General entity which represents problem/text/video material."""

    TYPES = (
        ('G', _('generic')),
        ('A', _('pre-assessment')),
        ('Z', _('post-assessment')),
    )

    order_with_respect_to = 'atype', 'collection'

    name = models.CharField(max_length=255)
    collection = models.ForeignKey('Collection', related_name='activities', null=True)
    tags = fields.CharField(
        max_length=255,
        help_text="Provide your tags separated by a comma.",
    )
    atype = fields.CharField(
        verbose_name="type", choices=TYPES, default='G', max_length=1,
        help_text="Choose 'pre/post-assessment' activity type to pin Activity to the start or the end of "
                  "the Collection."
    )
    difficulty = fields.FloatField(
        default='0.5',
        help_text="Provide float number in the range 0.0 - 1.0",
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    points = models.FloatField(blank=True, default=1)
    lti_consumer = models.ForeignKey(LtiConsumer, null=True)
    source_launch_url = models.URLField(max_length=255, null=True)
    source_name = fields.CharField(max_length=255, blank=True, null=True)
    source_context_id = fields.CharField(max_length=255, blank=True, null=True)
    # NOTE(wowkalucky): extra field 'order' is available (inherited from OrderedModel)

    class Meta:
        verbose_name_plural = 'Activities'
        unique_together = ("source_launch_url", "collection")
        ordering = 'atype', 'order'

    def __str__(self):
        return u'<Activity: {}>'.format(self.name)

    def get_absolute_url(self):
        return reverse('module:collection-detail', kwargs={'pk': self.collection.pk})

    def save(self, *args, **kwargs):
        """Extension which sends notification to the Adaptive engine that Activity is created/updated."""
        initial_id = self.id
        if initial_id:
            if not ENGINE.update_activity(self):
                raise ValidationError
            Log.objects.create(
                log_type=Log.ADMIN, action=Log.ACTIVITY_UPDATED,
                data=self.get_research_data()
            )
        super(Activity, self).save(*args, **kwargs)
        if not initial_id:
            if not ENGINE.add_activity(self):
                super(Activity, self).delete(*args, **kwargs)
                raise ValidationError
            Log.objects.create(
                log_type=Log.ADMIN, action=Log.ACTIVITY_CREATED,
                data=self.get_research_data()
            )

    def delete(self, *args, **kwargs):
        """Extension which sends notification to the Adaptive engine that Activity is deleted."""
        if not ENGINE.delete_activity(self):
            raise ValidationError
        Log.objects.create(
            log_type=Log.ADMIN, action=Log.ACTIVITY_DELETED,
            data=self.get_research_data()
        )
        super(Activity, self).delete(*args, **kwargs)

    @property
    def last_pre(self):
        """
        Has Activity last order number position in certain type sub-collection.

        :return: (bool)
        """
        last_pre = Activity.objects.filter(collection=self.collection, atype='A').last()
        return self.id == last_pre.id

    def get_research_data(self):
        return {'collection_id': self.collection_id, 'activity_id': self.id}


@python_2_unicode_compatible
class Log(models.Model):
    """
    Student actions log.

    Every time student opens/submits lti problem new Log created.
    """

    OPENED = 'O'
    SUBMITTED = 'S'
    ADMIN = 'A'
    LOG_TYPES = (
        (OPENED, 'Opened'),
        (SUBMITTED, 'Submitted'),
        (ADMIN, 'Admin'),
    )

    ACTIVITY_CREATED = 'AC'
    ACTIVITY_UPDATED = 'AU'
    ACTIVITY_DELETED = 'AD'
    COLLECTION_CREATED = 'CC'
    COLLECTION_UPDATED = 'CU'
    ACTIONS = (
        (ACTIVITY_CREATED, 'Activity created'),
        (ACTIVITY_UPDATED, 'Activity updated'),
        (ACTIVITY_DELETED, 'Activity deleted'),
        (COLLECTION_CREATED, 'Collection created'),
        (COLLECTION_UPDATED, 'Collection updated'),
    )

    sequence_item = models.ForeignKey('SequenceItem', null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    log_type = fields.CharField(choices=LOG_TYPES, max_length=32)
    answer = models.BooleanField(verbose_name='Is answer correct?', default=False)
    attempt = models.PositiveIntegerField(default=0)
    action = fields.CharField(choices=ACTIONS, max_length=2, null=True, blank=True)
    data = JSONField(default={}, blank=True)

    def __str__(self):
        if self.log_type == self.OPENED:
            return u'<Log[{}]: {}>'.format(self.get_log_type_display(), self.sequence_item)
        elif self.log_type == self.ADMIN:
            return u'<Log[{}]: {} ({})>'.format(
                self.get_log_type_display(),
                self.get_action_display(),
                self.data
            )
        else:
            return u'<Log[{}]: {}-{}[{}]>'.format(
                self.get_log_type_display(),
                self.sequence_item,
                self.answer,
                self.attempt
            )
