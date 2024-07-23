from rest_framework import serializers

from core.api.v1.serializers import LicenseStatementSerializer
from issue import models
from journal.models import SciELOJournal
from journal.api.v1.serializers import JournalSerializer
from location.api.v1.serializers import CitySerializer

class TocSectionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TocSection
        fields = [
            "plain_text",
        ]


class IssueSerializer(serializers.ModelSerializer):
    journal = serializers.SerializerMethodField()
    sections = TocSectionsSerializer(many=True, read_only=True)
    license = LicenseStatementSerializer(many=True, read_only=True)
    scielo_journal = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Issue
        fields = [
            "journal",
            "scielo_journal",
            "sections",
            "license",
            "number",
            "volume",
            "season",
            "year",
            "month",
            "supplement",
        ]

    def get_scielo_journal(self, obj):
        results = obj.journal.scielojournal_set.prefetch_related("journal_history").values(
            "issn_scielo", 
            "journal_acron",
            "collection__acron3",
            "journal_history__day",
            "journal_history__month",
            "journal_history__year",
            "journal_history__event_type",
            "journal_history__interruption_reason",
        )
        journal_dict = {}

        for item in results:
            journal_acron = item["journal_acron"]
            issn_scielo = item["issn_scielo"]

            journal_history = dict(
            collection_acron=item["collection__acron3"],
            day=item["journal_history__day"],
            month=item["journal_history__month"],
            year=item["journal_history__year"],
            event_type=item["journal_history__event_type"],
            interruption_reason=item["journal_history__interruption_reason"])

            if journal_acron not in journal_dict:
                journal_dict[journal_acron] = {
                    "issn_scielo": issn_scielo,
                    "journal_acron": journal_acron,
                    "journal_history": []
                }

            journal_dict[journal_acron]["journal_history"].append(journal_history)
        
        return list(journal_dict.values())

    def get_journal(self, obj):
        collection_acron3 = self.context.get("request").query_params.get("collection")
        if obj.journal:
            try:
                scielo_journal = obj.journal.scielojournal_set.get(collection__acron3=collection_acron3).issn_scielo
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
            }