from rest_framework import serializers

from core.api.v1.serializers import LanguageSerializer
from vocabulary.models import Keyword


class KeywordSerializer(serializers.ModelSerializer):
    language = LanguageSerializer(many=False, read_only=True)

    class Meta:
        model = Keyword
        fields = [
            # "vocabulary",
            "text",
            "language",
        ]
