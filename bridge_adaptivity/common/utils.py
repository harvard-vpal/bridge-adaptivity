"""
Get engine from CollectinOrder, get stub page and find last item in a sequence.
"""
from logging import getLogger

from django.http import Http404
from django.shortcuts import render

from module.models import Collection, CollectionGroup, CollectionOrder, Engine

log = getLogger(__name__)


def get_collection_collectiongroup_engine(collection_slug, group_slug, collectionorder_order):
    """
    Return collection and collection group by collection_slug, group_slug and collectionorder_order.
    """
    collection = Collection.objects.filter(slug=collection_slug).first()
    if not collection:
        log.exception("Collection with provided ID does not exist. Check configured launch url.")
        raise Http404('Bad launch_url collection ID.')

    collection_group = CollectionGroup.objects.filter(slug=group_slug).first()

    if collection_group is None:
        raise Http404(
            'The launch URL is not correctly configured. The group with the slug `{}` cannot be found.'
            .format(group_slug)
        )

    if collection not in collection_group.collections.all():
        raise Http404(
            'The launch URL is not correctly configured. Collection with the slug `{}` is not in group with slug `{}`'
            .format(collection_slug, group_slug)
        )
    # NOTE(AnadreyLikhoman): Using CollectionOrder to find engine (collection, group, order)
    collection_order = CollectionOrder.objects.filter(
        collection=collection,
        group=collection_group,
        order=collectionorder_order
    ).first()

    if collection_group:
        engine = collection_order.engine or Engine.get_default()
    else:
        engine = Engine.get_default()

    return collection, collection_group, engine, collection_order


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
