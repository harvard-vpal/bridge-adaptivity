class CollectionIdToContext(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(CollectionIdToContext, self).get_context_data(**kwargs)
        context['current_collection_id'] = self.kwargs.get('collection_id')
        return context
