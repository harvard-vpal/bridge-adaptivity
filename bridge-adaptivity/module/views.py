import logging

from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import ListView, CreateView, DetailView, UpdateView
from slumber.exceptions import HttpClientError

from api.backends.openedx import get_available_courses, get_content_provider
from module.forms import ActivityForm
from .models import (Collection, Activity, SequenceItem, Log, Sequence)

log = logging.getLogger(__name__)


class CollectionList(ListView):
    model = Collection
    context_object_name = 'collections'
    paginate_by = 10

    def get_queryset(self):
        return Collection.objects.filter(owner=self.request.user)


class CollectionCreate(CreateView):
    model = Collection
    fields = ['name', 'metadata', 'strict_forward']

    def form_valid(self, form):
        collection = form.save(commit=False)
        collection.owner = self.request.user
        collection.save()
        return super(CollectionCreate, self).form_valid(form)


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


class ActivityUpdate(UpdateView):
    model = Activity
    context_object_name = 'activity'
    fields = ActivityCreate.fields

    def get_context_data(self, **kwargs):
        context = super(ActivityUpdate, self).get_context_data(**kwargs)
        context['current_collection_id'] = self.kwargs.get('collection_id')
        return context


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
        position=sequence_item.position+1
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
            position=sequence_item.position+1
        )

    return redirect(reverse('module:sequence-item', kwargs={'pk': sequence_item_next.id}))


class SequenceComplete(DetailView):
    model = Sequence
    template_name = 'module/sequence_complete.html'
