from django.views.generic import CreateView
from django.views.generic import ListView

from .models import Collection


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
