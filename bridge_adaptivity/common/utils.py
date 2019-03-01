"""
Get engine from CollectinOrder, get stub page and find last item in a sequence.
"""
from logging import getLogger

from django.http import Http404
from django.shortcuts import render

from module.models import CollectionOrder, Engine

log = getLogger(__name__)


def get_collection_collectiongroup_engine(collection_order_slug):
    """
    Return collection and collection group by collection_slug, group_slug and collectionorder_order.
    """
    # NOTE(AnadreyLikhoman): Using CollectionOrder to find engine
    collection_order = CollectionOrder.objects.filter(slug=collection_order_slug).first()
    if not collection_order:
        log.exception("Collection Order with provided Slug does not exist. Check configured launch url.")
        raise Http404('Bad launch_url collection_order slug.')

    if collection_order:
        engine = collection_order.engine or Engine.get_default()
    else:
        engine = Engine.get_default()

    return engine, collection_order


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
