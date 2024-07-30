from rest_framework import serializers
from collections import defaultdict

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
    name = serializers.CharField(
        source="institution.institution.institution_identification.name"
    )

    class Meta:
        model = models.PublisherHistory
        fields = [
            "name",
        ]


class OwnerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        source="institution.institution.institution_identification.name"
    )

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
    publisher = PublisherSerializer(
        many=True, read_only=True, source="publisher_history"
    )
    owner = OwnerSerializer(many=True, read_only=True, source="owner_history")
    acronym = serializers.SerializerMethodField()
    scielo_journal = serializers.SerializerMethodField()
    title_in_database = serializers.SerializerMethodField()

    def get_acronym(self, obj):
        scielo_journal = obj.scielojournal_set.first()
        return scielo_journal.journal_acron if scielo_journal else None

    def get_scielo_journal(self, obj):
        results = models.SciELOJournal.objects.filter(journal=obj).prefetch_related("journal_history")
        journals = []
        for item in results:
            journal_dict = {
                'collection_acron': item.collection.acron3,
                'issn_scielo': item.issn_scielo,
                'journal_acron': item.journal_acron,
                'journal_history': [
                    {
                        'day': history.day,
                        'month': history.month,
                        'year': history.year,
                        'event_type': history.event_type,
                        'interruption_reason': history.interruption_reason,
                    } for history in item.journal_history.all()
                ],
            }
            journals.append(journal_dict)
            
        return journals

    def get_title_in_database(self, obj):
        title_in_database = obj.title_in_database.all()
        title_in_db = []
        for item in title_in_database:
            title_in_db_dict = {
                'name': item.indexed_at.name,
                'acronym': item.indexed_at.acronym,
                'url': item.indexed_at.url,
            }
            title_in_db.append(title_in_db_dict)
        return title_in_db

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
            "title_in_database",
        ]
