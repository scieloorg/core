from wagtail.models.sites import Site
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
    language = serializers.SerializerMethodField()

    class Meta:
        model = models.Mission
        fields = [
            "rich_text",
            "language",
        ]
    def get_language(self, obj):
        if obj.language is not None:
            return obj.language.code2
        return None    

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
    title_in_database = serializers.SerializerMethodField()
    url_logo = serializers.SerializerMethodField()
    mission = MissionSerializer(many=True, read_only=True)
    other_titles = serializers.SerializerMethodField()
    sponsor = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    copyright = serializers.SerializerMethodField()
    next_journal_title = serializers.SerializerMethodField()
    previous_journal_title = serializers.SerializerMethodField()
    toc_items = serializers.SerializerMethodField()
    wos_areas = serializers.SerializerMethodField()

    def get_institution_history(self, institution_history):
        if queryset := institution_history.all():
            return [{"name": str(item)} for item in queryset]

    def get_publisher(self, obj):
        return self.get_institution_history(obj.publisher_history)

    def get_owner(self, obj):
        return self.get_institution_history(obj.owner_history)

    def get_sponsor(self, obj):
        return self.get_institution_history(obj.sponsor_history)

    def get_copyright(self, obj):
        return self.get_institution_history(obj.copyright_holder_history)

    def get_acronym(self, obj):
        scielo_journal = obj.scielojournal_set.first()
        return scielo_journal.journal_acron if scielo_journal else None

    def get_scielo_journal(self, obj):
        results = models.SciELOJournal.objects.filter(journal=obj).prefetch_related(
            "journal_history"
        )
        journals = []
        for item in results:
            journal_dict = {
                "collection_acron": item.collection.acron3,
                "issn_scielo": item.issn_scielo,
                "journal_acron": item.journal_acron,
                "journal_history": [
                    {
                        "day": history.day,
                        "month": history.month,
                        "year": history.year,
                        "event_type": history.event_type,
                        "interruption_reason": history.interruption_reason,
                    }
                    for history in item.journal_history.all()
                ],
                "status": item.status,
            }
            journals.append(journal_dict)

        return journals

    def get_title_in_database(self, obj):
        title_in_database = obj.title_in_database.all()
        title_in_db = []
        for item in title_in_database:
            title_in_db_dict = {
                "title": item.title,
                "identifier": item.identifier,
                "name": item.indexed_at.name,
                "acronym": item.indexed_at.acronym,
                "url": item.indexed_at.url,
            }
            title_in_db.append(title_in_db_dict)
        return title_in_db

    def get_url_logo(self, obj):
        if obj.logo:
            domain = Site.objects.get(is_default_site=True).hostname
            domain = f"http://{domain}"
            return f"{domain}{obj.logo.file.url}"
        return None

    def get_email(self, obj):
        if obj.journal_email.all():
            return [email.email for email in obj.journal_email.all()]
        return None

    def get_other_titles(self, obj):
        if obj.other_titles.all():
            return [other_title.title for other_title in obj.other_titles.all()]
        return None

    def get_next_journal_title(self, obj):
        if obj.official and obj.official.next_journal_title:
            try:
                journal_new_title = models.Journal.objects.get(title__exact=obj.official.next_journal_title)
                issn_print = journal_new_title.official.issn_print
                issn_electronic = journal_new_title.official.issn_electronic
            except models.Journal.DoesNotExist:
                issn_print = None
                issn_electronic = None
            return {
                "next_journal_title": obj.official.next_journal_title,
                "issn_print": issn_print,
                "issn_electronic": issn_electronic,
            }

    def get_previous_journal_title(self, obj):
        if obj.official and obj.official.previous_journal_titles:
            try:
                old_journal = obj.official.old_title.get(
                    title__exact=obj.official.previous_journal_titles
                )
                old_issn_print = old_journal.issn_print
                old_issn_electronic = old_journal.issn_electronic
            except models.OfficialJournal.DoesNotExist:
                old_issn_print = None
                old_issn_electronic = None

            return {
                "previous_journal_title": obj.official.previous_journal_titles,
                "issn_print": old_issn_print,
                "issn_electronic": old_issn_electronic,
            }

    def get_toc_items(self, obj):
        if queryset := obj.journaltocsection_set.all():
            data = []
            for item in queryset:
                for section in item.toc_items.all():
                    data.append(
                        {
                            "value": section.text,
                            "language": (
                                section.language.code2 if section.language else None
                            ),
                        }
                    )
            return data

    def get_wos_areas(self, obj):
        if obj.wos_area.all():
            return [wos_area.value for wos_area in obj.wos_area.all()]
        return None

    class Meta:
        model = models.Journal
        fields = [
            "created",
            "updated",
            "official",
            "scielo_journal",
            "title",
            "short_title",
            "next_journal_title",
            "previous_journal_title",
            "other_titles",
            "acronym",
            "journal_use_license",
            "publisher",
            "owner",
            "sponsor",
            "copyright",
            "subject_descriptor",
            "subject",
            "toc_items",
            "submission_online_url",
            "email",
            "contact_address",
            "text_language",
            "doi_prefix",
            "title_in_database",
            "url_logo",
            "mission",
            "wos_areas",
        ]
