import hashlib
import importlib
import inspect
import logging
import math
import os
import uuid

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import fields
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from multiselectfield import MultiSelectField
from ordered_model.models import OrderedModel
import shortuuid
from slugger import AutoSlugField

from bridge_lti.models import BridgeUser, LtiContentSource, LtiUser, OutcomeService
from common.mixins.models import HasLinkedSequenceMixin, ModelFieldIsDefaultMixin
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
    """
    Load class from module.
    """
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

"""
Policy choices. Key is a policy name and value is a GradingPolicyClass.

GradingPolicyClass has __str__ method and it's string representation is GradingPolicy.public_name.
This hack is done to pass policy.summary_text and policy.detail_text to select policy widget's template, where these
variables are used to show popover message with description about each policy (bootstrap3 JS popover function).
"""
GRADING_POLICY_CHOICES = ((k, v) for k, v in GRADING_POLICY_NAME_TO_CLS.items())


class Sequence(models.Model):
    """
    Represents User's problem solving track.
    """

    lti_user = models.ForeignKey(LtiUser, on_delete=models.CASCADE)
    collection_order = models.ForeignKey('CollectionOrder', null=True, on_delete=models.CASCADE)
    completed = fields.BooleanField(default=False)
    lis_result_sourcedid = models.CharField(max_length=255, null=True)
    outcome_service = models.ForeignKey(OutcomeService, null=True, on_delete=models.CASCADE)

    metadata = JSONField(default={}, blank=True)

    # NOTE(yura.braiko) suffix is a hash to make unique user_id for the collection repetition feature.
    suffix = models.CharField(max_length=15, default='')

    class Meta:
        unique_together = ('lti_user', 'collection_order', 'suffix')

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

    def sequence_ui_details(self):
        """
        Create the context for the optional label on the student view.

        Context depends on the ModuleGroup's OPTION value.
        :return: str with the text for injecting into the label.
        """
        ui_options = self.collection_order.ui_option

        details_list = []
        for ui_option in ui_options:
            # NOTE(idegtiarov) conditions depend on ModuleGroup's OPTIONS
            if ui_option == CollectionOrder.OPTIONS[0][0]:
                details = (
                    f"{CollectionOrder.OPTIONS[0][1]}: {self.items.count()}/"
                    f"{self.collection_order.collection.activities.count()}"
                )
            elif ui_option == CollectionOrder.OPTIONS[1][0]:
                grade = self.collection_order.grading_policy.calculate_grade(self)
                # NOTE(andrey.lykhoman): Operations with float numbers can lead to the creation of some numbers in
                #     higher degrees after the decimal point.
                grade = round(grade * 100, 1)
                details = f"{CollectionOrder.OPTIONS[1][1]}: {grade}%"
            else:
                details = (
                    f"{CollectionOrder.OPTIONS[2][1]}: "
                    f"{self.items.filter(score__gt=0).count()}/{self.items.filter(score=0).count()}"
                )
            details_list.append(details)

        return details_list


class SequenceItem(models.Model):
    """
    Represents one User's step in problem solving track.
    """

    sequence = models.ForeignKey('Sequence', related_name='items', null=True, on_delete=models.CASCADE)
    activity = models.ForeignKey('Activity', null=True, on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=1)
    score = models.FloatField(null=True, blank=True, help_text="Grade policy: 'p' (problem's current score).")
    # NOTE(idegtiarov) suffix is a hash to make unique user_id for the Activity repetition feature.
    suffix = models.CharField(max_length=10, default='')

    is_problem = models.BooleanField(default=True)
    __origin_score = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__origin_score = self.score

    class Meta:
        verbose_name = "Sequence Item"
        verbose_name_plural = "Sequence Items"
        ordering = ['sequence', 'position']

    def __str__(self):
        return '<SequenceItem: {}={}>'.format(self.sequence, self.activity.name)

    def _add_suffix(self):
        """
        Add suffix to the SequenceItem if activity repetition is allowed.
        """
        if self.suffix:
            return
        self.suffix = hashlib.sha1(shortuuid.uuid().encode('utf-8')).hexdigest()[::4]  # Return 10 character uuid suffix

    def save(self, *args, **kwargs):
        """
        Extension sending notification to the Adaptive engine that score is changed.
        """
        if self.score != self.__origin_score:
            engine = self.sequence.collection_order.engine.engine_driver
            engine.submit_activity_answer(self)
            log.debug("Adaptive engine is updated with the grade for the {} activity in the SequenceItem {}".format(
                self.activity.name, self.id
            ))
        if self.activity.repetition > 1:
            self._add_suffix()
        self.is_problem = self.activity.is_problem
        super().save(*args, **kwargs)

    @property
    def user_id_for_consumer(self):
        return f'{self.sequence.lti_user.user_id}{self.sequence.suffix}{self.suffix}'


class GradingPolicy(ModelFieldIsDefaultMixin, models.Model):
    """
    Predefined set of Grading policy objects. Define how to grade collections.

    Field `name` if fulfilled from the correspondent choices in the form GradingPolicyForm.
    """

    name = models.CharField(max_length=20)  # Field name is not editable in admin UI.
    public_name = models.CharField(max_length=255)
    params = JSONField(default={}, blank=True, help_text="Policy parameters in json format.")
    engine = models.ForeignKey('Engine', blank=True, null=True, on_delete=models.CASCADE)
    is_default = models.BooleanField(default=False)

    @property
    def policy_cls(self):
        return GRADING_POLICY_NAME_TO_CLS[self.name]

    def policy_instance(self, **kwargs):
        return self.policy_cls(policy=self, **kwargs)

    def calculate_grade(self, sequence):
        policy = self.policy_cls(policy=self, sequence=sequence)
        return math.floor(policy.grade * 1000) / 1000

    def __str__(self):
        return "{}, public_name: {} params: {}{}".format(
            self.name, self.public_name, self.params,
            ", IS DEFAULT POLICY" if self.is_default else ""
        )


class Collection(models.Model):
    """Set of Activities (problems) for a module."""

    name = fields.CharField(max_length=255)
    slug = AutoSlugField(
        populate_from='name',
        unique=True,
        db_index=True,
        help_text="Add the slug for the collection. If field empty slug will be created automatically.",
        verbose_name='slug id'
    )
    owner = models.ForeignKey(BridgeUser, on_delete=models.CASCADE)
    metadata = fields.CharField(max_length=255, blank=True, null=True)
    updated_at = fields.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('owner', 'name')

    def __str__(self):
        return '<Collection: {}>'.format(self.name)

    def save(self, *args, **kwargs):
        """Extension cover method with logging."""
        initial_id = self.id
        super().save(*args, **kwargs)
        tasks.sync_collection_engines.apply_async(
            kwargs={'collection_slug': self.slug, 'created_at': self.updated_at},
            countdown=settings.CELERY_DELAY_SYNC_TASK,
        )

        if initial_id:
            Log.objects.create(
                log_type=Log.ADMIN, action=Log.COLLECTION_UPDATED,
                data={'collection_slug': self.slug}
            )
        else:
            Log.objects.create(
                log_type=Log.ADMIN, action=Log.COLLECTION_CREATED,
                data={'collection_slug': self.slug}
            )

    def get_absolute_url(self):
        return reverse('module:collection-list')


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


class CollectionOrder(HasLinkedSequenceMixin, OrderedModel):

    OPTIONS = (
        ('AT', _('Questions viewed/total')),
        ('EP', _('Earned grade')),
        ('RW', _('Answers right/wrong'))
    )

    slug = models.SlugField(unique=True, default=uuid.uuid4, editable=True, db_index=True)
    group = models.ForeignKey('ModuleGroup', on_delete=models.CASCADE)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE)
    grading_policy = models.OneToOneField('GradingPolicy', blank=True, null=True, on_delete=models.CASCADE)
    engine = models.ForeignKey(Engine, blank=True, null=True, on_delete=models.CASCADE)
    strict_forward = fields.BooleanField(default=True)
    ui_option = MultiSelectField(
        choices=OPTIONS, blank=True, help_text="Add an optional UI block to the student view"
    )

    ui_next = models.BooleanField(
        default=False, help_text="Add an optional NEXT button under the embedded unit."
    )
    congratulation_message = fields.BooleanField(default=False)

    order_with_respect_to = 'group'

    class Meta:
        ordering = ('group', 'order')

    @property
    def get_selected_ui_options(self):
        res_list = self.get_ui_option_list()
        if self.ui_next:
            res_list.append(_('Additional NEXT Button'))
        return res_list

    def get_launch_url(self):
        return "{}{}".format(settings.BRIDGE_HOST, reverse("lti:launch", kwargs={'collection_order_slug': self.slug}))


class ModuleGroup(models.Model):
    """
    Represents Module Group.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    atime = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(BridgeUser, on_delete=models.CASCADE)
    slug = models.UUIDField(unique=True, default=uuid.uuid4, editable=False, db_index=True)

    collections = models.ManyToManyField(
        Collection, related_name='collection_groups', blank=True, through='CollectionOrder'
    )
    contributors = models.ManyToManyField(
        BridgeUser, related_name='module_groups', blank=True, through='ContributorPermission'
    )

    @property
    def ordered_collections(self):
        """
        Return tuple of tuples of CollectionOrder and result sequence_set.exists() method.
        """
        return (
            (col_order, col_order.sequence_set.exists())
            for col_order in CollectionOrder.objects.filter(group=self).order_by('order')
        )

    def __str__(self):
        return "<Group of Collections: {}>".format(self.name)

    def get_absolute_url(self):
        return reverse('module:group-detail', kwargs={'group_slug': self.slug})

    def get_collection_order_by_order(self, order):
        """
        Return CollectionOrder object filtered by order and group.
        """
        return CollectionOrder.objects.filter(group=self, order=order).first()

    def has_linked_active_sequences(self):
        return CollectionOrder.objects.filter(group=self, sequence__completed=False).exists()

    def has_linked_sequences(self):
        return CollectionOrder.objects.filter(group=self, sequence__isnull=False).exists()


class ContributorPermission(models.Model):
    user = models.ForeignKey(BridgeUser, on_delete=models.CASCADE)
    group = models.ForeignKey(ModuleGroup, on_delete=models.CASCADE)
    # Note(AndreyLykhoman): Change this field to field with the possibility to select more than one option for select.
    full_permission = models.BooleanField(default=True)


class Activity(OrderedModel):
    """General entity which represents problem/text/video material."""

    TYPES = (
        ('G', _('generic')),
        ('A', _('pre-assessment')),
        ('Z', _('post-assessment')),
    )

    order_with_respect_to = 'atype', 'collection'

    name = models.CharField(max_length=255)
    collection = models.ForeignKey('Collection', related_name='activities', null=True, on_delete=models.CASCADE)
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
    lti_content_source = models.ForeignKey(LtiContentSource, null=True, on_delete=models.CASCADE)
    source_launch_url = models.URLField(max_length=255, null=True)
    source_name = fields.CharField(max_length=255, blank=True, null=True)
    # NOTE(wowkalucky): extra field 'order' is available (inherited from OrderedModel)

    # `stype` - means source_type or string_type.
    stype = models.CharField(
        "Type of the activity", help_text="(problem, video, html, etc.)", max_length=25, blank=True, null=True
    )
    # Number of possible repetition of the activity in the sequence
    repetition = models.PositiveIntegerField(
        default=1, help_text="The number of possible repetition of the Activity in the sequence."
    )

    @property
    def is_problem(self):
        return self.stype in settings.PROBLEM_ACTIVITY_TYPES

    class Meta:
        verbose_name_plural = 'Activities'
        unique_together = ("source_launch_url", "collection")
        ordering = 'atype', 'order'

    def __str__(self):
        return '<Activity: {}>'.format(self.name)

    def get_absolute_url(self):
        return reverse('module:collection-detail', kwargs={'slug': self.collection.slug})

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
        super().save(*args, **kwargs)
        self.collection.save()

    def delete(self, *args, **kwargs):
        """Extension which sends notification to the Adaptive engine that Activity is deleted."""
        Log.objects.create(
            log_type=Log.ADMIN, action=Log.ACTIVITY_DELETED,
            data=self.get_research_data()
        )
        super().delete(*args, **kwargs)
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

    sequence_item = models.ForeignKey('SequenceItem', null=True, blank=True, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    log_type = fields.CharField(choices=LOG_TYPES, max_length=32)
    answer = models.BooleanField(verbose_name='Is answer correct?', default=False)
    attempt = models.PositiveIntegerField(default=0)
    action = fields.CharField(choices=ACTIONS, max_length=2, null=True, blank=True)
    data = JSONField(default={}, blank=True)

    def __str__(self):
        if self.log_type == self.OPENED:
            return '<Log[{}]: {}>'.format(self.get_log_type_display(), self.sequence_item)
        elif self.log_type == self.ADMIN:
            return '<Log[{}]: {} ({})>'.format(
                self.get_log_type_display(),
                self.get_action_display(),
                self.data
            )
        else:
            return '<Log[{}]: {}-{}[{}]>'.format(
                self.get_log_type_display(),
                self.sequence_item,
                self.answer,
                self.attempt
            )
