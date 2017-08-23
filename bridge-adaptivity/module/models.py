from django.db import models
from django.db.models import fields
from django.urls import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from bridge_lti.models import LtiUser, BridgeUser, LtiConsumer


@python_2_unicode_compatible
class Sequence(models.Model):
    """
    Represents User's problem solving track.
    """
    lti_user = models.ForeignKey(LtiUser)
    collection = models.ForeignKey('Collection')
    completed = fields.BooleanField(default=False)
    total_points = models.FloatField(blank=True, null=True)

    class Meta:
        unique_together = ('lti_user', 'collection')

    def __str__(self):
        return '<Sequence: {}>'.format(self.lti_user)


@python_2_unicode_compatible
class SequenceItem(models.Model):
    """
    Represents one User's step in problem solving track.
    """
    sequence = models.ForeignKey('Sequence', null=True)
    activity = models.ForeignKey('Activity', null=True)
    position = models.PositiveIntegerField()

    class Meta:
        verbose_name = "Sequence Item"
        verbose_name_plural = "Sequence Items"
        ordering = ['position']

    def __str__(self):
        return '<SequenceItem: {}={}>'.format(self.sequence, self.activity.name)


@python_2_unicode_compatible
class Collection(models.Model):
    """
    Set of Activities (problems) for a module.
    """
    name = fields.CharField(max_length=255)
    owner = models.ForeignKey(BridgeUser)
    threshold = models.FloatField(blank=True, null=True)
    metadata = fields.CharField(max_length=255, blank=True, null=True)
    strict_forward = fields.BooleanField(default=True)

    class Meta:
        unique_together = ('owner', 'name')

    def __str__(self):
        return '<Collection: {}>'.format(self.name)

    def get_absolute_url(self):
        return reverse('module:collection-list')


@python_2_unicode_compatible
class Activity(models.Model):
    """
    General entity which represents problem/text/video material.
    """
    LEVELS = (
        ('low', _('low')),
        ('medium', _('medium')),
        ('high', _('high')),
    )

    name = models.CharField(max_length=255)
    collection = models.ForeignKey('Collection', null=True)
    tags = fields.CharField(max_length=255, blank=True, null=True)
    difficulty = fields.CharField(choices=LEVELS, default='medium', max_length=32)
    points = models.FloatField(blank=True, null=True)
    lti_consumer = models.ForeignKey(LtiConsumer, null=True)
    source_launch_url = models.URLField(max_length=255, unique=True, null=True)
    source_name = fields.CharField(max_length=255, blank=True, null=True)
    source_context_id = fields.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Activities'

    def __str__(self):
        return '<Activity: {}>'.format(self.name)

    def get_absolute_url(self):
        return reverse('module:collection-detail', kwargs={'pk': self.collection.pk})

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
            return '<Log: {}>'.format(self.sequence_item)
        else:
            return '<Log: {}-{}[{}]>'.format(self.sequence_item, self.answer, self.attempt)


