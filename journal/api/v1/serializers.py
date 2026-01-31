from rest_framework import serializers
from wagtail.models.sites import Site

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


class JournalOrganizationSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_acronym = serializers.CharField(source="organization.acronym", read_only=True)
    organization_location = serializers.SerializerMethodField()
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    journal_title = serializers.CharField(source="journal.title", read_only=True)
    display_name = serializers.SerializerMethodField()
    is_current = serializers.SerializerMethodField()
    
    def get_organization_location(self, obj):
        if obj.organization and obj.organization.location:
            return obj.organization.location.data
        return None
    
    def get_display_name(self, obj):
        """Retorna o nome da organização ou original_data se organização não existir"""
        if obj.organization:
            return obj.organization.name
        return obj.original_data
    
    def get_is_current(self, obj):
        """Verifica se a organização está ativa (sem data de fim ou data futura)"""
        if not obj.end_date:
            return True
        from datetime import date
        return obj.end_date > date.today()
    
    class Meta:
        model = models.JournalOrganization
        fields = [
            "id",
            "role",
            "role_display", 
            "display_name",
            "organization_name",
            "organization_acronym", 
            "organization_location",
            "journal_title",
            "start_date",
            "end_date",
            "is_current",
            "original_data",
            "created",
            "updated",
        ]


# class PublisherSerializer(serializers.ModelSerializer):
#     """
#     DEPRECATED: This serializer is deprecated and will be removed in a future version.
#     Use JournalOrganizationSerializer with role="publisher" instead.
#     """
#     name = serializers.CharField(
#         source="institution.institution.institution_identification.name"
#     )

#     class Meta:
#         model = models.PublisherHistory
#         fields = [
#             "name",
#         ]


# class OwnerSerializer(serializers.ModelSerializer):
#     """
#     DEPRECATED: This serializer is deprecated and will be removed in a future version.
#     Use JournalOrganizationSerializer with role="owner" instead.
#     """
#     name = serializers.CharField(
#         source="institution.institution.institution_identification.name"
#     )

#     class Meta:
#         model = models.OwnerHistory
#         fields = [
#             "name",
#         ]


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


class JournalTableOfContentsSerializer(serializers.ModelSerializer):
    language = serializers.SerializerMethodField()
    collection_acron = serializers.SerializerMethodField()

    class Meta:
        model = models.JournalTableOfContents
        fields = [
            "text",
            "code", 
            "language",
            "collection_acron",
        ]

    def get_language(self, obj):
        if obj.language:
            return obj.language.code2
        return None

    def get_collection_acron(self, obj):
        if obj.collection:
            return obj.collection.acron3
        return None


class JournalSerializer(serializers.ModelSerializer):
    # Serializadores para campos de relacionamento, como 'official', devem corresponder aos campos do modelo.
    # Basic journal information
    official = OfficialJournalSerializer(many=False, read_only=True)
    acronym = serializers.SerializerMethodField()
    other_titles = serializers.SerializerMethodField()
    next_journal_title = serializers.SerializerMethodField()
    previous_journal_title = serializers.SerializerMethodField()
    
    # Classification and subjects
    subject_descriptor = SubjectDescriptorSerializer(many=True, read_only=True)
    subject = SubjectSerializer(many=True, read_only=True)
    wos_areas = serializers.SerializerMethodField()
    
    # Language and content
    text_language = LanguageSerializer(many=True, read_only=True)
    mission = MissionSerializer(many=True, read_only=True)
    # TODO: DEPRECATED - será removido em versão futura, usar table_of_contents
    toc_items = serializers.SerializerMethodField()
    # NOVO: substitui toc_items
    table_of_contents = serializers.SerializerMethodField()
    
    # Organizations and roles
    publisher = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    sponsor = serializers.SerializerMethodField()
    copyright = serializers.SerializerMethodField()
    
    # License and legal
    journal_use_license = serializers.SerializerMethodField()
    
    # Contact information
    email = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    
    # External data and indexing
    scielo_journal = serializers.SerializerMethodField()
    title_in_database = serializers.SerializerMethodField()
    
    # Media and presentation
    url_logo = serializers.SerializerMethodField()

    def get_institution_history(self, institution_history):
        """DEPRECATED: Mantido para compatibilidade com API legacy"""
        if queryset := institution_history.all():
            return [{"name": str(item)} for item in queryset]
    
    def get_organization_by_role(self, obj, role):
        """Busca organizações por role no JournalOrganization"""
        organizations = obj.organizations.filter(role=role)
        if organizations.exists():
            items = []
            for item in organizations:
                org = item.organization
                if not org:
                    continue
                items.append({
                    "name": org.name or item.original_data,
                    "acronym": org.acronym,
                    "url": org.url,
                    "location": org.location.data if org.location else None,
                    "start_date": item.start_date,
                    "end_date": item.end_date,
                })
            return items
        return None

    def get_publisher(self, obj):
        # Primeiro tenta buscar do novo modelo JournalOrganization
        result = self.get_organization_by_role(obj, "publisher")
        if result:
            return result
        # Fallback para o modelo legacy para compatibilidade
        return self.get_institution_history(obj.publisher_history)

    def get_owner(self, obj):
        # Primeiro tenta buscar do novo modelo JournalOrganization
        result = self.get_organization_by_role(obj, "owner")
        if result:
            return result
        # Fallback para o modelo legacy para compatibilidade
        return self.get_institution_history(obj.owner_history)

    def get_sponsor(self, obj):
        # Primeiro tenta buscar do novo modelo JournalOrganization
        result = self.get_organization_by_role(obj, "sponsor")
        if result:
            return result
        # Fallback para o modelo legacy para compatibilidade
        return self.get_institution_history(obj.sponsor_history)

    def get_copyright(self, obj):
        # Primeiro tenta buscar do novo modelo JournalOrganization
        result = self.get_organization_by_role(obj, "copyright_holder")
        if result:
            return result
        # Fallback para o modelo legacy para compatibilidade
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
                "collection_acron": item.collection.acron3 if item.collection else None,
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
        """
        DEPRECATED: Este método será removido em versão futura.
        Use get_table_of_contents() que fornece dados mais estruturados.
        
        Relacionamento antigo: journaltocsection_set -> toc_items
        Novo relacionamento: journaltableofcontents_set
        """
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

    def get_table_of_contents(self, obj):
        """
        NOVO: Retorna seções do sumário usando JournalTableOfContents.
        Substitui o get_toc_items() com dados mais estruturados.
        """
        if queryset := obj.journaltableofcontents_set.all():
            data = []
            for item in queryset:
                data.append({
                    "text": item.text,
                    "code": item.code,
                    "language": item.language.code2 if item.language else None,
                    "collection_acron": item.collection.acron3 if item.collection else None,
                })
            return data
        return []

    def get_wos_areas(self, obj):
        if obj.wos_area.all():
            return [wos_area.value for wos_area in obj.wos_area.all()]
        return None

    def get_location(self, obj):
        if obj.contact_location:
            return obj.contact_location.data

    def get_journal_use_license(self, obj):
        if obj.journal_use_license:
            return obj.journal_use_license.license_type
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
            "organizations",
            "publisher",
            "owner",
            "sponsor",
            "copyright",
            "subject_descriptor",
            "subject",
            "toc_items",  # TODO: DEPRECATED - remover em versão futura
            "table_of_contents",  # NOVO: substitui toc_items
            "submission_online_url",
            "email",
            "contact_name",
            "contact_address",
            "location",
            "text_language",
            "doi_prefix",
            "title_in_database",
            "url_logo",
            "mission",
            "wos_areas",
        ]
