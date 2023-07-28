from rest_framework import serializers

from core.api.v1.serializers import LanguageSerializer
from doi.models import DOI


class DoiSerializer(serializers.ModelSerializer):
    language = LanguageSerializer(many=False, read_only=True)

    class Meta:
        model = DOI
        fields = [
            "value",
            "language",
        ]
        datatables_always_serialize = ("id",)
