from rest_framework import serializers

from vocabulary.models import (
    Keyword,
    )
from core.api.v1.serializers import LanguageSerializer


class KeywordSerializer(serializers.ModelSerializer):
    language = LanguageSerializer(many=False, read_only=True)

    class Meta:
        model = Keyword
        fields = [
            # "vocabulary",
            "text",
            "language",
            ]