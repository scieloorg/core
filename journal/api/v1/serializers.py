from rest_framework import serializers

from core.api.v1.serializers import LanguageSerializer
from journal import models



class OfficialJournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OfficialJournal
        fields = [
            "title",
            "issn_print",
            "issn_electronic",
            "iso_short_title",
            "issnl",
        ]
        datatables_always_serialize = ("id",)


class SubjectDescriptorSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SubjectDescriptor
        fields = [
            "value",
        ]


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Subject
        fields = [
            "value",
        ]


class JournalUseLicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.JournalLicense
        fields = [
            "license_type",
        ]


class PublisherSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='institution.institution.institution_identification.name')

    class Meta:
        model = models.PublisherHistory
        fields = [
            "name",
        ]


class OwnerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='institution.institution.institution_identification.name')
    
    class Meta:
        model = models.OwnerHistory
        fields = [
            "name",
        ]


class JournalSerializer(serializers.ModelSerializer):
    # Serializadores para campos de relacionamento, como 'official', devem corresponder aos campos do modelo.
    official = OfficialJournalSerializer(many=False, read_only=True)
    subject_descriptor = SubjectDescriptorSerializer(many=True, read_only=True)
    subject = SubjectSerializer(many=True, read_only=True)
    text_language = LanguageSerializer(many=True, read_only=True)
    journal_use_license = JournalUseLicenseSerializer(many=False, read_only=True)
    publisher = PublisherSerializer(many=True, read_only=True, source="publisher_history")
    owner = OwnerSerializer(many=True, read_only=True, source="owner_history")
    acronym = serializers.SerializerMethodField()
    scielo_journal = serializers.SerializerMethodField()

    def get_acronym(self, obj):
        scielo_journal = obj.scielojournal_set.first()
        return scielo_journal.journal_acron if scielo_journal else None


    def get_scielo_journal(self, obj):
        scielo_journals = obj.scielojournal_set.prefetch_related('journal_history').values(
                'journal_acron', 
                'issn_scielo', 
                'journal_history__day', 
                'journal_history__month', 
                'journal_history__year', 
                'journal_history__event_type', 
                'journal_history__interruption_reason'
            )
        renamed_results = [
            {
                "journal_acron": item["journal_acron"],
                "issn_scielo": item["issn_scielo"],
                "day": item["journal_history__day"],
                "month": item["journal_history__month"],
                "year": item["journal_history__year"],
                "event_type": item["journal_history__event_type"],
                "interruption_reason": item["journal_history__interruption_reason"],
            } 
            for item in scielo_journals
        ]
        return renamed_results

    class Meta:
        model = models.Journal
        fields = [
            "official",
            "scielo_journal",
            "title",
            "short_title",
            "acronym",
            "journal_use_license",
            "publisher",
            "owner",
            "subject_descriptor",
            "subject",
            "text_language",
        ]