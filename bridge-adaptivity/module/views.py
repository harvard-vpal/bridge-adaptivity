import logging

from django.contrib.auth.decorators import login_required
from django import forms
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from slumber.exceptions import HttpClientError

from api.backends.openedx import get_available_courses, get_content_provider
from module.forms import ActivityForm
from .models import (Collection, Activity, SequenceItem, Log, Sequence)

log = logging.getLogger(__name__)


@method_decorator(login_required, name='dispatch')
class CollectionList(ListView):
    model = Collection
    context_object_name = 'collections'
    paginate_by = 10
    ordering = ['id']

    def get_queryset(self):
        return Collection.objects.filter(owner=self.request.user)


@method_decorator(login_required, name='dispatch')
class CollectionCreate(CreateView):
    model = Collection
    fields = ['name', 'owner', 'threshold', 'metadata', 'strict_forward']

    def get_form(self):
        # FIXME(wowkalucky): improve 'unique_together' default validation message
        form = super(CollectionCreate, self).get_form()
        form.fields['owner'].initial = self.request.user
        form.fields['owner'].widget = forms.HiddenInput(attrs={'readonly': True})
        return form


@method_decorator(login_required, name='dispatch')
class CollectionDetail(DetailView):
    model = Collection
    context_object_name = 'collection'

    def get_context_data(self, **kwargs):
        context = super(CollectionDetail, self).get_context_data(**kwargs)
        context['render_fields'] = ['name', 'tags', 'difficulty', 'points', 'source_name']
        context['activities'] = Activity.objects.filter(collection=self.object)
        context['source_courses'] = self.get_content_courses()
        context['activity_form'] = ActivityForm(initial={
            'collection': self.object,
            'lti_consumer': get_content_provider(),
        })
        return context

    @staticmethod
    def get_content_courses():
        try:
            return get_available_courses()
        except HttpClientError:
            log.exception(
                "There are no active LTI Content Providers. Enable one by setting via Bridge admin site"
                "LtiConsumer.is_active=True."
            )
            return []


@method_decorator(login_required, name='dispatch')
class ActivityCreate(CreateView):
    model = Activity
    fields = ['name', 'tags', 'difficulty', 'points', 'source_launch_url', 'source_name', 'source_context_id']

    def form_valid(self, form):
        activity = form.save(commit=False)
        collection = Collection.objects.get(pk=self.kwargs.get('collection_id'))
        activity.collection = collection
        activity.lti_consumer = get_content_provider()
        activity.save()
        return super(ActivityCreate, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(ActivityCreate, self).get_context_data(**kwargs)
        context['current_collection_id'] = self.kwargs.get('collection_id')
        return context

    def get_success_url(self):
        return reverse('module:collection-detail', kwargs={'pk': self.kwargs.get('collection_id')})


@method_decorator(login_required, name='dispatch')
class ActivityUpdate(UpdateView):
    model = Activity
    context_object_name = 'activity'
    fields = ActivityCreate.fields

    def get_context_data(self, **kwargs):
        context = super(ActivityUpdate, self).get_context_data(**kwargs)
        context['current_collection_id'] = self.kwargs.get('collection_id')
        return context


@method_decorator(login_required, name='dispatch')
class ActivityDelete(DeleteView):
    model = Activity

    def get_success_url(self):
        return reverse('module:collection-detail', kwargs={'pk': self.object.collection.id})


class SequenceItemDetail(DetailView):
    model = SequenceItem
    context_object_name = 'sequence_item'
    template_name = 'module/sequence_item.html'

    def get_context_data(self, **kwargs):
        context = super(SequenceItemDetail, self).get_context_data(**kwargs)
        context['sequence_items'] = SequenceItem.objects.filter(sequence=self.object.sequence)

        Log.objects.create(
            sequence_item=self.object,
            log_type=Log.OPENED
        )

        return context


def sequence_item_next(request, pk):
    sequence_item = get_object_or_404(SequenceItem, pk=pk)

    sequence_item_next = SequenceItem.objects.filter(
        sequence=sequence_item.sequence,
        position=sequence_item.position + 1
    ).first()

    if sequence_item_next is None:
        try:
            activity = sequence_item.sequence.collection.activity_set.all()[sequence_item.position]
        except IndexError:
            sequence_item.sequence.completed = True
            sequence_item.sequence.save()
            return redirect(reverse('module:sequence-complete', kwargs={'pk': sequence_item.sequence_id}))

        sequence_item_next = SequenceItem.objects.create(
            sequence=sequence_item.sequence,
            activity=activity,
            position=sequence_item.position + 1
        )

    return redirect(reverse('module:sequence-item', kwargs={'pk': sequence_item_next.id}))


class SequenceComplete(DetailView):
    model = Sequence
    template_name = 'module/sequence_complete.html'
