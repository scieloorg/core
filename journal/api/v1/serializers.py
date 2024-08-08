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
    other_titles = serializers.SerializerMethodField()
    sponsor = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    copyright = serializers.SerializerMethodField()
    next_journal_title = serializers.SerializerMethodField()
    previous_journal_titles = serializers.SerializerMethodField()

    def get_publisher(self, obj):
        if queryset := obj.publisher_history.all():
            return [{"name": str(item)} for item in queryset]

    def get_owner(self, obj):
        if queryset := obj.owner_history.all():
            return [{"name": str(item)} for item in queryset]

    def get_sponsor(self, obj):
        if queryset := obj.sponsor_history.all():
            return [{"name": str(item)} for item in queryset]

    def get_copyright(self, obj):
        if queryset := obj.copyright_holder_history.all():
            return [{"name": str(item)} for item in queryset]

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
            }
            journals.append(journal_dict)

        return journals

    def get_url_logo(self, obj):
        if obj.logo:
            domain = Site.objects.get(is_default_site=True).hostname
            domain = f"https://{domain}"
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
        if obj.official.next_journal_title:
            return {
                "next_journal_title": obj.official.next_journal_title,
                "issn_print": obj.official.new_title.issn_print,
                "issn_electronic": obj.official.new_title.issn_electronic,
            }

    def get_previous_journal_titles(self, obj):
        if obj.official.previous_journal_titles:
            try:
                old_issn_print = obj.official.old_title.get(
                    title__icontains=obj.official.previous_journal_titles
                ).issn_print
            except models.OfficialJournal.DoesNotExist:
                old_issn_print = None

            try:
                old_issn_electronic = obj.official.old_title.get(
                    title__icontains=obj.official.previous_journal_titles
                ).issn_electronic
            except models.OfficialJournal.DoesNotExist:
                old_issn_electronic = None

            return {
                "previous_journal_title": obj.official.previous_journal_titles,
                "issn_print": old_issn_print,
                "issn_electronic": old_issn_electronic,
            }

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
