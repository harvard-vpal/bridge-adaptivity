import logging

from django.db import models
from django.db.models import fields
from django.urls import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from ordered_model.models import OrderedModel

from bridge_lti.models import LtiUser, BridgeUser, LtiConsumer, OutcomeService
from module import ENGINE


log = logging.getLogger(__name__)


@python_2_unicode_compatible
class Sequence(models.Model):
    """
    Represents User's problem solving track.
    """
    lti_user = models.ForeignKey(LtiUser)
    collection = models.ForeignKey('Collection')
    completed = fields.BooleanField(default=False)
    lis_result_sourcedid = models.CharField(max_length=255, null=True)
    outcome_service = models.ForeignKey(OutcomeService, null=True)

    class Meta:
        unique_together = (('lti_user', 'collection'), ('lis_result_sourcedid', 'outcome_service'))

    def __str__(self):
        return '<Sequence: {}>'.format(self.lti_user)


@python_2_unicode_compatible
class SequenceItem(models.Model):
    """
    Represents one User's step in problem solving track.
    """
    sequence = models.ForeignKey('Sequence', related_name='items', null=True)
    activity = models.ForeignKey('Activity', null=True)
    position = models.PositiveIntegerField(default=1)
    score = models.FloatField(null=True, blank=True, help_text="Grade policy: 'p' (problem's current score).")

    class Meta:
        verbose_name = "Sequence Item"
        verbose_name_plural = "Sequence Items"
        ordering = ['sequence', 'position']

    def __str__(self):
        return u'<SequenceItem: {}={}>'.format(self.sequence, self.activity.name)


@python_2_unicode_compatible
class Collection(models.Model):
    """
    Set of Activities (problems) for a module.
    """
    name = fields.CharField(max_length=255)
    owner = models.ForeignKey(BridgeUser)
    threshold = models.PositiveIntegerField(blank=True, default=0, help_text="Grade policy: 'Q'")
    metadata = fields.CharField(max_length=255, blank=True, null=True)
    strict_forward = fields.BooleanField(default=True)

    class Meta:
        unique_together = ('owner', 'name')

    def __str__(self):
        return u'<Collection: {}>'.format(self.name)

    def get_absolute_url(self):
        return reverse('module:collection-list')


@python_2_unicode_compatible
class Activity(OrderedModel):
    """
    General entity which represents problem/text/video material.
    """
    LEVELS = (
        ('l', _('low')),
        ('m', _('medium')),
        ('h', _('high')),
    )

    TYPES = (
        ('G', _('generic')),
        ('A', _('pre-assessment')),
        ('Z', _('post-assessment')),
    )

    order_with_respect_to = 'atype', 'collection'

    name = models.CharField(max_length=255)
    collection = models.ForeignKey('Collection', related_name='activities', null=True)
    tags = fields.CharField(max_length=255, blank=True, null=True)
    atype = fields.CharField(verbose_name="type", choices=TYPES, default='G', max_length=1)
    difficulty = fields.CharField(choices=LEVELS, default='m', max_length=1)
    points = models.FloatField(blank=True, default=1)
    lti_consumer = models.ForeignKey(LtiConsumer, null=True)
    source_launch_url = models.URLField(max_length=255, null=True)
    source_name = fields.CharField(max_length=255, blank=True, null=True)
    source_context_id = fields.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Activities'
        unique_together = ("source_launch_url", "collection")
        ordering = 'atype', 'order'

    def __str__(self):
        return u'<Activity: {}>'.format(self.name)

    def get_absolute_url(self):
        return reverse('module:collection-detail', kwargs={'pk': self.collection.pk})

    def save(self, *args, **kwargs):
        """
        Extend save() method with sending notification to the Adaptive engine that Activity is created/updated
        """
        if Activity.objects.filter(id=self.id):
            ENGINE.update_activity(self)
        else:
            ENGINE.add_activity(self)
        super(Activity, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Extend delete() method with sending notification to the Adaptive engine that Activity is deleted
        """
        ENGINE.delete_activity(self)
        super(Activity, self).delete(*args, **kwargs)


@python_2_unicode_compatible
class Log(models.Model):
    """
    Student actions log.

    Every time student opens/submits lti problem new Log created.
    """
    OPENED = 'O'
    SUBMITTED = 'S'
    LOG_TYPES = (
        (OPENED, 'Opened'),
        (SUBMITTED, 'Submitted'),
    )
    sequence_item = models.ForeignKey('SequenceItem', null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    log_type = fields.CharField(choices=LOG_TYPES, max_length=32)
    answer = models.BooleanField(verbose_name='Is answer correct?', default=False)
    attempt = models.PositiveIntegerField(default=0)

    def __str__(self):
        if self.log_type == self.OPENED:
            return u'<Log: {}>'.format(self.sequence_item)
        else:
            return u'<Log: {}-{}[{}]>'.format(self.sequence_item, self.answer, self.attempt)
