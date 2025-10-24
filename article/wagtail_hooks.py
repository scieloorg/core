from typing import Any

from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from article.models import (
    Article,
    ArticleExporter,
    ArticleFormat,
    ArticleFunding,
    ArticleSource,
    ArticleAvailability,
    AMArticle,
)
from collection.models import Collection
from config.menu import get_menu_order


class ArticleAvailabilitySnippetViewSet(SnippetViewSet):
    model = ArticleAvailability
    menu_label = _("Article Availability")
    menu_icon = "link"
    menu_order = 1

    list_display = ["url", "collection", "available", "error", "updated"]
    list_filter = ["collection", "lang", "fmt", "available", "error"]
    search_fields = [
        "url",
        "article__sps_pkg_name",
        "article__pid_v3",
        "article__pid_v2",
    ]
    icon = "link"
    menu_label = _("Article Availability")


# register_snippet(ArticleAvailabilitySnippetViewSet)


class ArticleSnippetViewSet(SnippetViewSet):
    model = Article
    menu_label = _("Article")
    menu_icon = "folder"
    menu_order = 1

    list_display = (
        "sps_pkg_name",
        "pid_v3",
        "pid_v2",
        "is_classic_public",
        "is_new_public",
        "valid",
        "data_status",
        "created",
        "updated",
    )
    list_filter = [
        "is_public",
        "is_classic_public",
        "is_new_public",
        "data_status",
        "valid",
        "journal__scielojournal__collection",
    ]
    search_fields = (
        "titles__plain_text",
        "pid_v2",
        "doi__value",
        "sps_pkg_name",
        "pid_v3",
    )


class ArticleExporterSnippetViewSet(SnippetViewSet):
    model = ArticleExporter
    menu_label = _("Article Export")
    menu_icon = "folder"
    menu_order = 100

    list_display = ("parent", "collection", "destination", "status", "updated")
    list_filter = (
        "collection",
        "destination",
        "status",
    )
    search_fields = ("parent__pid_v3", "parent__sps_pkg_name")


class ArticleFormatSnippetViewSet(SnippetViewSet):
    model = ArticleFormat
    menu_label = _("Article Format")
    menu_icon = "folder"
    menu_order = 500

    list_display = (
        "article",
        "format_name",
        "version",
        "valid",
        "created",
        "updated",
    )
    list_filter = ("format_name", "version", "valid")
    search_fields = (
        "article__sps_pkg_name",
        "format_name",
        "version",
    )


# register_snippet(ArticleFormatSnippetViewSet)


class ArticleFundingSnippetViewSet(SnippetViewSet):
    model = ArticleFunding
    menu_label = _("Article Funding")
    menu_icon = "folder"
    menu_order = 200

    list_display = ("award_id", "funding_source")
    search_fields = (
        "award_id",
        "funding_source__name",
        "funding_source__institution_type",
    )


class ArticleSourceSnippetViewSet(SnippetViewSet):
    """Custom ViewSet for ArticleSource snippets"""

    model = ArticleSource
    menu_label = _("Article Sources")
    menu_icon = "doc-full"
    menu_order = 200

    list_display = [
        "am_article",
        "pid_provider_xml",
        "status",
        "source_date",
        "updated",
    ]
    list_filter = [
        "status",
        "am_article__collection",
    ]
    search_fields = ["url", "pid_provider_xml__v3", "am_article__collection__acronym"]
    ordering = ["-updated"]
    list_per_page = 25


# register_snippet(ArticleSourceSnippetViewSet)

class AMArticleSnippetViewSet(SnippetViewSet):
    """ViewSet for AMArticle (Legacy Article) snippets"""
    
    model = AMArticle
    menu_label = _("Legacy Articles")
    menu_icon = "doc-full-inverse"
    menu_order = 300
    
    list_display = [
        "pid",
        "collection",
        "new_record",
        "status",
        "processing_date",
        "updated",
    ]
    list_filter = [
        "status",
        "collection",
        "processing_date",
    ]
    search_fields = [
        "pid",
        "collection__acronym",
        "new_record__pid_v3",
        "new_record__sps_pkg_name",
    ]
    ordering = ["-updated"]
    list_per_page = 25


class ArticleSnippetViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Articles")
    menu_icon = "folder-open-inverse"
    menu_order = get_menu_order("article")
    items = (
        ArticleSnippetViewSet,
        ArticleAvailabilitySnippetViewSet,
        ArticleExporterSnippetViewSet,
        ArticleFormatSnippetViewSet,
        ArticleFundingSnippetViewSet,
        ArticleSourceSnippetViewSet,
        AMArticleSnippetViewSet,
    )


register_snippet(ArticleSnippetViewSetGroup)
