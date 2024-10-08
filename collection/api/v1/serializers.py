from rest_framework import serializers

from collection import models


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Collection
        fields = [
            "acron3",
            "acron2",
            "code",
            "domain",
            "main_name",
            "status",
            "foundation_date",
            "collection_type",
            "is_active",
        ]