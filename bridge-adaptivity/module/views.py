from django.urls import reverse
from django.views.generic import ListView, CreateView, DetailView
from django.views.generic import UpdateView

from .models import Collection, Activity


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
        context['model_fields'] = ActivityCreate.fields
        context['activities'] = Activity.objects.filter(collection=self.object)
        return context


class ActivityCreate(CreateView):
    model = Activity
    fields = ['name', 'tag', 'difficulty', 'points', 'launch_url']

    def form_valid(self, form):
        activity = form.save(commit=False)
        collection = Collection.objects.get(pk=self.kwargs.get('collection_id'))
        activity.collection = collection
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
    fields = ['name', 'tag', 'difficulty', 'points', 'launch_url']

    def get_context_data(self, **kwargs):
        context = super(ActivityUpdate, self).get_context_data(**kwargs)
        context['current_collection_id'] = self.kwargs.get('collection_id')
        return context
