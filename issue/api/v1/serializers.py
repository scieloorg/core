from rest_framework import serializers

from core.api.v1.serializers import LicenseSerializer
from issue import models
from journal.api.v1.serializers import JournalSerializer
from location.api.v1.serializers import CitySerializer


class TocSectionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TocSection
        fields = [
            "plain_text",
        ]


class IssueSerializer(serializers.ModelSerializer):
    journal = JournalSerializer(many=False, read_only=True)
    sections = TocSectionsSerializer(many=True, read_only=True)
    license = LicenseSerializer(many=True, read_only=True)
    city = CitySerializer(many=False, read_only=True)

    class Meta:
        model = models.Issue
        fields = [
            "journal",
            "sections",
            "license",
            "number",
            "volume",
            "season",
            "year",
            "month",
            "supplement",
            "city",
        ]
