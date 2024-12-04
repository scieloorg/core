from rest_framework import serializers

from article import models
from core.api.v1.serializers import LanguageSerializer, LicenseStatementSerializer
from doi.api.v1.serializers import DoiSerializer
from institution.api.v1.serializers import SponsorSerializer, PublisherSerializer
from issue.api.v1.serializers import IssueSerializer, TocSectionsSerializer
from journal.api.v1.serializers import JournalSerializer
from journal.models import SciELOJournal
from researcher.api.v1.serializers import ResearcherSerializer
from vocabulary.api.v1.serializers import KeywordSerializer
from pid_provider.models import PidProviderXML

class FundingsSerializer(serializers.ModelSerializer):
    funding_source = SponsorSerializer(many=False, read_only=True)

    class Meta:
        model = models.ArticleFunding
        fields = [
            "award_id",
            "funding_source",
        ]


class TitleSerializer(serializers.ModelSerializer):
    language = LanguageSerializer(many=False, read_only=True)

    class Meta:
        model = models.DocumentTitle
        fields = ["plain_text", "language"]  ## MUDAR NOME ??


class ArticleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ArticleType
        fields = [
            "text",
        ]


class DocumentAbstractSerializer(serializers.ModelSerializer):
    language = LanguageSerializer(many=False, read_only=True)

    class Meta:
        model = models.DocumentAbstract
        fields = [
            "rich_text",
            "plain_text",
            "language",
        ]


class TocSectionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TocSection
        fields = [
            # "text",
            "plain_text",
            # "rich_text",
        ]


class ArticleSerializer(serializers.ModelSerializer):
    journal = serializers.SerializerMethodField() 
    publisher = PublisherSerializer(many=False, read_only=True)
    titles = TitleSerializer(many=True, read_only=True)
    doi = DoiSerializer(many=True, read_only=True)
    abstracts = DocumentAbstractSerializer(many=True, read_only=True)
    researchers = ResearcherSerializer(many=True, read_only=True)
    languages = LanguageSerializer(many=True, read_only=True)
    fundings = FundingsSerializer(many=True, read_only=True)
    article_type = ArticleTypeSerializer(many=False, read_only=True)
    toc_sections = TocSectionsSerializer(many=True, read_only=True)
    license = LicenseStatementSerializer(many=True, read_only=True)
    issue = IssueSerializer(many=False, read_only=True)
    keywords = KeywordSerializer(many=True, read_only=True)
    xml_link = serializers.SerializerMethodField()


    def get_journal(self, obj):
        if obj.journal:
            scielo_journal = SciELOJournal.objects.get(journal=obj.journal).issn_scielo
            return {
                "title": obj.journal.title,
                "short_title": obj.journal.short_title,
                "issn_print": obj.journal.official.issn_print,
                "issn_electronic": obj.journal.official.issn_electronic,
                "issnl":  obj.journal.official.issnl,
                "journal_acron": scielo_journal.journal_acron,
            }
        else:
            return None
            

    def get_xml_link(self, obj):
        if obj:
            pid_provider = PidProviderXML.objects.get(v3=obj.pid_v3)
            # TODO
            # Adicionar dominio no link?
            return {"xml_link": pid_provider.current_version.file.url}

    class Meta:
        model = models.Article
        fields = [
            "journal",
            "publisher",
            "titles",
            "doi",
            "pid_v2",
            "pid_v3",
            "abstracts",
            "researchers",
            "languages",
            "pub_date_day",
            "pub_date_month",
            "pub_date_year",
            "fundings",
            "article_type",
            "toc_sections",
            "license",
            "issue",
            "first_page",
            "last_page",
            "elocation_id",
            "keywords",
        ]
