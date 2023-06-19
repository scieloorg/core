from rest_framework import serializers
from article import models

from doi.api.v1.serializers import DoiSerializer
from journal.api.v1.serializers import JournalSerialiazer
from institution.api.v1.serializers import SponsorSerializer
from core.api.v1.serializers import (
    LanguageSerializer,
    LicenseSerializer,
)
from researcher.api.v1.serializers import ResearcherSerializer
from issue.api.v1.serializers import IssueSerializer
from vocabulary.api.v1.serializers import KeywordSerializer


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
            "text",
        ]


class ArticleSerializer(serializers.ModelSerializer):
    journal = JournalSerialiazer(many=False, read_only=True)
    publisher = SponsorSerializer(many=True, read_only=True)
    titles = TitleSerializer(many=True, read_only=True)
    doi = DoiSerializer(many=True, read_only=True)
    abstracts = DocumentAbstractSerializer(many=True, read_only=True)
    researchers = ResearcherSerializer(many=True, read_only=True)
    languages = LanguageSerializer(many=True, read_only=True)
    fundings = FundingsSerializer(many=True, read_only=True)
    article_type = ArticleTypeSerializer(many=False, read_only=True)
    toc_sections = TocSectionsSerializer(many=True, read_only=True)
    license = LicenseSerializer(many=True, read_only=True)
    issue = IssueSerializer(many=False, read_only=True)
    keywords = KeywordSerializer(many=True, read_only=True)

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
        datatables_always_serialize = ("id",)
