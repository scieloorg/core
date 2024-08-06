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


class MissionSerializer(serializers.ModelSerializer):
    code2 = serializers.CharField(source="language.code2")
    class Meta:
        model = models.Mission
        fields = [
            "rich_text",
            "code2",
        ]


class JournalSerializer(serializers.ModelSerializer):
    # Serializadores para campos de relacionamento, como 'official', devem corresponder aos campos do modelo.
    official = OfficialJournalSerializer(many=False, read_only=True)
    subject_descriptor = SubjectDescriptorSerializer(many=True, read_only=True)
    subject = SubjectSerializer(many=True, read_only=True)
    text_language = LanguageSerializer(many=True, read_only=True)
    journal_use_license = JournalUseLicenseSerializer(many=False, read_only=True)
    publisher = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    acronym = serializers.SerializerMethodField()
    scielo_journal = serializers.SerializerMethodField()
    url_logo = serializers.SerializerMethodField()
    mission = MissionSerializer(many=True, read_only=True)
    issn_print = serializers.CharField(source="official.issn_print")
    issn_electronic = serializers.CharField(source="official.issn_electronic")
    next_journal_title = serializers.CharField(source="official.next_journal_title")
    previous_journal_titles = serializers.CharField(source="official.previous_journal_titles")
    other_titles = serializers.SerializerMethodField()
    sponsor = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    copyright = serializers.SerializerMethodField()

    def get_institution_data(self, history):
        data = []
        for record in history.all():
            if record.institution:
                data.append({"name": record.institution.institution.institution_identification.name})
        return data if data else None
    
    def get_publisher(self, obj):
       return self.get_institution_data(obj.publisher_history)

    def get_owner(self, obj):
        return self.get_institution_data(obj.owner_history)

    def get_sponsor(self, obj):
        return self.get_institution_data(obj.sponsor_history)

    def get_copyright(self, obj):
        return self.get_institution_data(obj.copyright_holder_history)

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

    def get_url_logo(self, obj):
        try:
            return models.JournalLogo.objects.get(journal=obj).url_logo

        except models.JournalLogo.DoesNotExist:
            return None
        except models.JournalLogo.MultipleObjectsReturned:
            return obj.title

    def get_email(self, obj):
        if obj.journal_email.all():
            return [email.email for email in obj.journal_email.all()]
        return None

    def get_other_titles(self, obj):
        if obj.other_titles.all():
            return [other_title.title for other_title in obj.other_titles.all()]
        return None
    

    class Meta:
        model = models.Journal
        fields = [
            "official",
            "scielo_journal",
            "title",
            "short_title",
            "next_journal_title",
            "previous_journal_titles",
            "other_titles",
            "acronym",
            "issn_print",
            "issn_electronic",
            "journal_use_license",
            "publisher",
            "owner",
            "subject_descriptor",
            "subject",
            "submission_online_url",
            "email",
            "contact_address",
            "text_language",
            "url_logo",
            "mission",
            "sponsor",
            "copyright",
        ]
