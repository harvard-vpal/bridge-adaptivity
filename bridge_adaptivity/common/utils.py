"""
Extra methods for all django modules.
"""
from logging import getLogger

from django.http import Http404
from django.shortcuts import render

from module.models import CollectionOrder, Engine

log = getLogger(__name__)


def get_engine_and_collection_order(collection_order_slug):
    """
    Return engine and CollectionOrder by CollectionOrder slug.
    """
    # NOTE(AnadreyLikhoman): Using CollectionOrder to find engine
    collection_order = CollectionOrder.objects.filter(slug=collection_order_slug).first()
    if not collection_order:
        log.error(
            f"Collection_Order with the slug: {collection_order_slug} does not exist. Please check lti launch url."
        )
        raise Http404(f'Bad slug of the collection_order in the lti launch url: ({collection_order_slug})')
    return collection_order.engine or Engine.get_default(), collection_order


def stub_page(
    request, title='announcement', message='coming soon!', tip='this adaptivity sequence is about to start.', **kwargs
):
    """
    Render stub page, announcement page is default.
    """
    context = {'title': title, 'message': message, 'tip': tip}
    context.update(kwargs)
    return render(
        request,
        template_name="bridge_lti/announcement.html",
        context=context
    )


def find_last_sequence_item(sequence, strict_forward):
    """
    Find out the last item in the sequence.

    :param sequence: Sequence instance.
    :param strict_forward: boolean glag, which is shown whether collection is strict forward.
    :return: instance of the "last" SequenceItem.
    """
    sequence_items = sequence.items.all()
    last = sequence_items.order_by().last()
    if strict_forward and sequence_items.count() > 1 and last.is_problem and last.score is None:
        return sequence_items[len(sequence_items) - 2]
    return last
