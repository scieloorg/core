from rest_framework import serializers

from core.api.v1.serializers import LicenseSerializer, LanguageSerializer
from issue import models
from journal.models import SciELOJournal
from location.api.v1.serializers import CitySerializer


class TocSectionsSerializer(serializers.ModelSerializer):
    language = LanguageSerializer(many=False, read_only=True)

    class Meta:
        model = models.TocSection
        fields = [
            "plain_text",
            "language"
        ]


class IssueSerializer(serializers.ModelSerializer):
    journal = serializers.SerializerMethodField()
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

    def get_journal(self, obj):
        if obj.journal:
            scielo_journal = SciELOJournal.objects.get(journal=obj.journal).issn_scielo
            return {
                "title": obj.journal.title,
                "short_title": obj.journal.short_title,
                "issn_print": obj.journal.official.issn_print,
                "issn_electronic": obj.journal.official.issn_electronic,
                "issnl":  obj.journal.official.issnl,
                "scielo_journal": scielo_journal,
            }
        else:
            return None