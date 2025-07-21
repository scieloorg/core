from rest_framework import serializers

from core.api.v1.serializers import LicenseStatementSerializer
from issue import models
from journal.models import SciELOJournal


class TocSectionsSerializer(serializers.ModelSerializer):
    language = serializers.CharField(source="language.code2")

    class Meta:
        model = models.TocSection
        fields = [
            "plain_text",
            "language",
        ]


class IssueSerializer(serializers.ModelSerializer):
    journal = serializers.SerializerMethodField()
    sections = TocSectionsSerializer(many=True, read_only=True)
    license = LicenseStatementSerializer(many=True, read_only=True)

    class Meta:
        model = models.Issue
        fields = [
            "created",
            "updated",
            "journal",
            "sections",
            "license",
            "number",
            "volume",
            "season",
            "year",
            "month",
            "supplement",
        ]

    def get_journal(self, obj):
        collection_acron3 = self.context.get("request").query_params.get("collection")
        if obj.journal:
            try:
                scielo_journal = obj.journal.scielojournal_set.get(
                    collection__acron3=collection_acron3
                ).issn_scielo
            except SciELOJournal.DoesNotExist:
                scielo_journal = None
            return {
                "title": obj.journal.title,
                "short_title": obj.journal.short_title,
                "issn_print": obj.journal.official.issn_print,
                "issn_electronic": obj.journal.official.issn_electronic,
                "issnl": obj.journal.official.issnl,
                "scielo_journal": scielo_journal,
                "collection_acron": obj.journal.scielojournal_set.first().collection.acron3,
                "license": (
                    obj.journal.journal_use_license.license_type
                    if obj.journal.journal_use_license
                    else None
                ),
                "publisher": [
                    publisher.institution.institution.institution_identification.name
                    for publisher in obj.journal.publisher_history.all()
                    if publisher.institution
                    and publisher.institution.institution
                    and publisher.institution.institution.institution_identification
                ],
                "nlmtitle": [medline.name for medline in obj.journal.indexed_at.all()],
            }
