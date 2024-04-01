from rest_framework import serializers

from core.models import Language, LicenseStatement


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = [
            "code2",
            "name",
        ]
        datatables_always_serialize = ("id",)


class LicenseStatementSerializer(serializers.ModelSerializer):
    language = LanguageSerializer(many=False, read_only=True)

    class Meta:
        model = LicenseStatement
        fields = [
            "url",
            "license_p",
            "language",
        ]
