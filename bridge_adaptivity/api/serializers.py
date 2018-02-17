from rest_framework import serializers

from module.models import Activity, Collection


class ActivitySerializer(serializers.ModelSerializer):
    """
    Serializer for Activity API view set.

    Serializer is based on the Activity model's fields.
    """

    class Meta:
        model = Activity
        fields = '__all__'


class CollectionSerializer(serializers.ModelSerializer):
    """
    Serializer for Collection API view set.

    Serializer is based on the Collection model's fields.
    """

    class Meta:
        model = Collection
        fields = '__all__'
