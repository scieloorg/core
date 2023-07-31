from rest_framework import serializers

from core.models import Language, License


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = [
            "code2",
        ]
        datatables_always_serialize = ("id",)


class LicenseSerializer(serializers.ModelSerializer):
    language = LanguageSerializer(many=False, read_only=True)

    class Meta:
        model = License
        fields = [
            "url",
            "license_p",
            "language",
        ]
