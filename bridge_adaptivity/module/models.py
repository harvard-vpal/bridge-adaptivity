import importlib
import inspect
import logging
import os
import uuid

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import fields
from django.urls import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from ordered_model.models import OrderedModel

from bridge_lti.models import BridgeUser, LtiConsumer, LtiUser, OutcomeService
from common.mixins.models import ModelFieldIsDefaultMixin
from module import tasks

log = logging.getLogger(__name__)


def _discover_applicable_modules(folder_name='engines', file_startswith='engine_'):
    modules = []
    for name in os.listdir(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), folder_name
    )):
        if name.startswith(file_startswith) and name.endswith('.py'):
            modules.append((name[:-len('.py')], name[len(file_startswith):-len('.py')]))
    return modules


def _load_cls_from_applicable_module(module_path, mod_name, class_startswith=None, class_endswith=None):
    """Load class from module."""
    module = None
    try:
        cls_module = importlib.import_module('{}.{}'.format(module_path, mod_name))
    except ImportError:
        log.error("Could not load module_path={}, mod_name={}".format(module_path, mod_name))
        raise
    for attr in inspect.getmembers(cls_module):
        if class_endswith and attr[0].endswith(class_endswith):
            module = attr[1]
        elif class_startswith and attr[0].startswith(class_startswith):
            module = attr[1]
    return module


ENGINES = _discover_applicable_modules(folder_name='engines', file_startswith='engine_')

GRADING_POLICY_MODULES = _discover_applicable_modules(folder_name='policies', file_startswith='policy_')
GRADING_POLICY_NAME_TO_CLS = {
    name: _load_cls_from_applicable_module("module.policies", file_name, class_endswith="GradingPolicy")
    for file_name, name in GRADING_POLICY_MODULES
}
GRADING_POLICY_CHOICES = ((k, v.public_name) for k, v in GRADING_POLICY_NAME_TO_CLS.items())


@python_2_unicode_compatible
class Sequence(models.Model):
    """Represents User's problem solving track."""

    lti_user = models.ForeignKey(LtiUser)
    collection = models.ForeignKey('Collection')
    group = models.ForeignKey('CollectionGroup', null=True)

    completed = fields.BooleanField(default=False)
    lis_result_sourcedid = models.CharField(max_length=255, null=True)
    outcome_service = models.ForeignKey(OutcomeService, null=True)

    metadata = JSONField(default={}, blank=True)

    class Meta:
        unique_together = (('lti_user', 'collection', 'group'), ('lis_result_sourcedid', 'outcome_service'))

    def __str__(self):
        return '<Sequence[{}]: {}>'.format(self.id, self.lti_user)

    def fulfil_sequence_metadata(self, lti_params, launch_params):
        """
        Automate fulfilling sequence metadata field with launch_params equal to lti_params.

        :param lti_params: iterable object with the required lti parameters names
        :param launch_params: dict with the launch lti parameters received in launch lti request
        """
        meta_dict = {}
        for param in lti_params:
            if param in launch_params:
                meta_dict[param] = launch_params[param]
        if meta_dict:
            self.metadata = meta_dict
            self.save()


@python_2_unicode_compatible
class SequenceItem(models.Model):
    """Represents one User's step in problem solving track."""

    sequence = models.ForeignKey('Sequence', related_name='items', null=True)
    activity = models.ForeignKey('Activity', null=True)
    position = models.PositiveIntegerField(default=1)
    score = models.FloatField(null=True, blank=True, help_text="Grade policy: 'p' (problem's current score).")

    is_problem = models.BooleanField(default=True)
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
            engine = self.sequence.group.engine.engine_driver
            engine.submit_activity_answer(self)
            log.debug("Adaptive engine is updated with the grade for the {} activity in the SequenceItem {}".format(
                self.activity.name, self.id
            ))
        self.is_problem = self.activity.is_problem
        super(SequenceItem, self).save(*args, **kwargs)


@python_2_unicode_compatible
class Course(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    slug = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(BridgeUser)

    def get_absolute_url(self):
        return reverse('module:course-detail', kwargs={'course_slug': self.slug})

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class GradingPolicy(ModelFieldIsDefaultMixin, models.Model):
    """
    Predefined set of Grading policy objects. Define how to grade collections.

    Field `name` if fulfilled from the correspondent choices in the form GradingPolicyForm.
    """

    name = models.CharField(max_length=20)  # Field name is not editable in admin UI.
    public_name = models.CharField(max_length=255)
    threshold = models.PositiveIntegerField(blank=True, default=0, help_text="Grade policy: 'Q'")
    is_default = models.BooleanField(default=False)

    @property
    def policy_cls(self):
        return GRADING_POLICY_NAME_TO_CLS[self.name]

    def policy_instance(self, **kwargs):
        return self.policy_cls(policy=self, **kwargs)

    def calculate_grade(self, sequence):
        policy = self.policy_cls(policy=self, sequence=sequence)
        return policy.grade

    def __str__(self):
        return "{}, public_name: {} threshold: {}{}".format(
            self.name, self.public_name, self.threshold,
            ", IS DEFAULT POLICY" if self.is_default else ""
        )


@python_2_unicode_compatible
class Collection(models.Model):
    """Set of Activities (problems) for a module."""

    name = fields.CharField(max_length=255)
    owner = models.ForeignKey(BridgeUser)
    metadata = fields.CharField(max_length=255, blank=True, null=True)
    strict_forward = fields.BooleanField(default=True)
    updated_at = fields.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('owner', 'name')

    def __str__(self):
        return u'<Collection: {}>'.format(self.name)

    def save(self, *args, **kwargs):
        """Extension cover method with logging."""
        initial_id = self.id
        super(Collection, self).save(*args, **kwargs)
        tasks.sync_collection_engines.apply_async(
            kwargs={'collection_id': self.id, 'created_at': self.updated_at},
            countdown=settings.CELERY_DELAY_SYNC_TASK,
        )

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

    def get_launch_url(self, group):
        return "{}{}".format(
            settings.BRIDGE_HOST,
            reverse("lti:launch", kwargs={'collection_id': self.id, 'group_slug': group.slug}))


@python_2_unicode_compatible
class Engine(ModelFieldIsDefaultMixin, models.Model):
    """Defines engine settings."""

    DEFAULT_ENGINE = 'engine_mock'
    DRIVER = None

    engine = models.CharField(choices=ENGINES, default=DEFAULT_ENGINE, max_length=100)
    engine_name = models.CharField(max_length=255, blank=True, null=True, unique=True)
    host = models.URLField(blank=True, null=True)
    token = models.CharField(max_length=255, blank=True, null=True)
    lti_parameters = models.TextField(
        default='',
        blank=True,
        help_text=_("LTI parameters to sent to the engine, use comma separated string")
    )
    is_default = fields.BooleanField(default=False, help_text=_("If checked Engine will be used as the default!"))

    class Meta:
        unique_together = ('host', 'token')

    def __str__(self):
        return "Engine: {}".format(self.engine_name)

    @classmethod
    def create_default(cls):
        return cls.objects.create(
            engine=cls.DEFAULT_ENGINE,
            engine_name='Mock',
            is_default=True
        )

    @property
    def engine_driver(self):
        if not self.DRIVER:
            driver = _load_cls_from_applicable_module('module.engines', self.engine, class_startswith='Engine')
            # NOTE(idegtiarov) Currently, statement coves existent engines modules. Improve in case new engine will be
            # added to the engines package.
            if self.engine.endswith('mock'):
                engine_driver = driver()
            else:
                engine_driver = driver(**{'HOST': self.host, 'TOKEN': self.token})
            self.DRIVER = engine_driver
        return self.DRIVER

    @property
    def lti_params(self):
        return (param.strip() for param in self.lti_parameters.split(','))


@python_2_unicode_compatible
class CollectionGroup(models.Model):
    """Represents Collections Group."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    atime = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(BridgeUser)
    slug = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, related_name='course_groups', blank=True, null=True, on_delete=models.SET_NULL)

    grading_policy = models.OneToOneField('GradingPolicy', blank=True, null=True)
    collections = models.ManyToManyField(Collection, related_name='collection_groups', blank=True)

    engine = models.ForeignKey(Engine)

    def __str__(self):
        return u"CollectionGroup: {}".format(self.name)

    def get_absolute_url(self):
        return reverse('module:group-detail', kwargs={'group_slug': self.slug})


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
        blank=True,
        null=True,
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

    # `stype` - means source_type or string_type.
    stype = models.CharField(
        "Type of the activity", help_text="(problem, video, html, etc.)", max_length=25, blank=True, null=True
    )

    @property
    def is_problem(self):
        return self.stype in settings.PROBLEM_ACTIVITY_TYPES

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
            Log.objects.create(
                log_type=Log.ADMIN, action=Log.ACTIVITY_UPDATED,
                data=self.get_research_data()
            )
        else:
            Log.objects.create(
                log_type=Log.ADMIN, action=Log.ACTIVITY_CREATED,
                data=self.get_research_data()
            )
        super(Activity, self).save(*args, **kwargs)
        self.collection.save()

    def delete(self, *args, **kwargs):
        """Extension which sends notification to the Adaptive engine that Activity is deleted."""
        Log.objects.create(
            log_type=Log.ADMIN, action=Log.ACTIVITY_DELETED,
            data=self.get_research_data()
        )
        super(Activity, self).delete(*args, **kwargs)
        self.collection.save()

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
