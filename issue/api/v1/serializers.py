from rest_framework import serializers

from core.api.v1.serializers import LicenseStatementSerializer
from issue import models
from journal.models import SciELOJournal


class AMIssueSerializer(serializers.ModelSerializer):
    collection = serializers.CharField(source="collection.acron3")

    class Meta:
        model = models.AMIssue
        fields = [
            "pid",
            "collection",
        ]


class SectionsSerializer(serializers.ModelSerializer):
    """
    Serializer que usa TableOfContents para expor dados das seções.
    Mantém o nome 'sections' para compatibilidade da API.
    """
    text = serializers.CharField(source="journal_toc.text")
    code = serializers.CharField(source="journal_toc.code", allow_null=True)
    language = serializers.SerializerMethodField()
    collection_acron = serializers.SerializerMethodField()

    class Meta:
        model = models.TableOfContents
        fields = [
            "text",
            "code",
            "language",
            "collection_acron",
            "sort_order",
        ]

    def get_language(self, obj):
        if obj.journal_toc and obj.journal_toc.language:
            return obj.journal_toc.language.code2
        return None

    def get_collection_acron(self, obj):
        if obj.journal_toc and obj.journal_toc.collection:
            return obj.journal_toc.collection.acron3
        return None


class IssueTitleSerializer(serializers.ModelSerializer):
    """
    Serializer para títulos do Issue.
    """
    language = serializers.CharField(source="language.code2")

    class Meta:
        model = models.IssueTitle
        fields = [
            "title",
            "language",
        ]


class BibliographicStripSerializer(serializers.ModelSerializer):
    """
    Serializer para tiras bibliográficas do Issue.
    """
    language = serializers.CharField(source="language.code2")

    class Meta:
        model = models.BibliographicStrip
        fields = [
            "text",
            "language",
        ]


class IssueSerializer(serializers.ModelSerializer):
    journal = serializers.SerializerMethodField()
    legacy_issue = AMIssueSerializer(many=True, read_only=True)
    sections = SectionsSerializer(source="table_of_contents", many=True, read_only=True)
    license = LicenseStatementSerializer(many=True, read_only=True)
    issue_titles = IssueTitleSerializer(source="issue_title", many=True, read_only=True)
    bibliographic_strips = BibliographicStripSerializer(source="bibliographic_strip", many=True, read_only=True)
    issue_folder = serializers.CharField(read_only=True)

    class Meta:
        model = models.Issue
        fields = [
            "created",
            "updated",
            "journal",
            "volume",
            "number",
            "supplement",
            "year",
            "season",
            "month",
            "order",
            "issue_pid_suffix",
            "issue_folder",
            "legacy_issue",
            "sections",
            "issue_titles",
            "bibliographic_strips",
            "license",
        ]

    def get_journal(self, obj):
        collection_acron3 = self.context.get("request").query_params.get("collection")
        if not obj.journal:
            return None
            
        try:
            # Tentar obter o SciELOJournal da collection especificada
            if collection_acron3:
                scielo_journal = obj.journal.scielojournal_set.get(
                    collection__acron3=collection_acron3
                )
                issn_scielo = scielo_journal.issn_scielo
                collection_acron = collection_acron3
            else:
                # Se não especificado, pegar o primeiro SciELOJournal
                scielo_journal = obj.journal.scielojournal_set.first()
                if scielo_journal:
                    issn_scielo = scielo_journal.issn_scielo
                    collection_acron = scielo_journal.collection.acron3
                else:
                    issn_scielo = None
                    collection_acron = None
                    
        except SciELOJournal.DoesNotExist:
            issn_scielo = None
            collection_acron = None
            
        # Obter dados do journal oficial
        official = getattr(obj.journal, 'official', None)
        
        return {
            "title": obj.journal.title,
            "short_title": obj.journal.short_title,
            "issn_print": official.issn_print if official else None,
            "issn_electronic": official.issn_electronic if official else None,
            "issnl": official.issnl if official else None,
            "scielo_journal": issn_scielo,
            "collection_acron": collection_acron,
            "license": (
                obj.journal.journal_use_license.license_type
                if hasattr(obj.journal, 'journal_use_license') and obj.journal.journal_use_license
                else None
            ),
            "publisher": [
                publisher.institution.institution.institution_identification.name
                for publisher in obj.journal.publisher_history.all()
                if (publisher.institution
                    and publisher.institution.institution
                    and publisher.institution.institution.institution_identification)
            ],
            "nlmtitle": [
                medline.name 
                for medline in obj.journal.indexed_at.all()
                if medline.name
            ],
        }
