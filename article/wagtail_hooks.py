from typing import Any

from django.contrib.admin import SimpleListFilter
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.db.models.query import QuerySet
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail_modeladmin.options import ModelAdmin, ModelAdminGroup, modeladmin_register
from wagtail_modeladmin.views import CreateView

from article.models import (  # AbstractModel,; Category,; Title,
    Article,
    ArticleExporter,
    ArticleFormat,
    ArticleFunding,
    ArticleSource,
    ArticleAvailability,
)
from collection.models import Collection
from config.menu import get_menu_order


class ArticleAvailabilitySnippetViewSet(SnippetViewSet):
    model = ArticleAvailability
    
    list_display = ["article", "collection", "lang", "fmt", "available", "url"]
    list_filter = ["collection", "lang", "available", "fmt"]
    search_fields = ["url", "article__title"]
    icon = "link"
    menu_label = _("Article Availability")

register_snippet(ArticleAvailabilitySnippetViewSet)


class CollectionFilter(SimpleListFilter):
    title = _("Collection")
    parameter_name = "collection"

    def lookups(self, request, model_admin):
        collections = Collection.objects.filter(is_active=True)
        return [(collection.id, collection.main_name) for collection in collections]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(journal__scielojournal__collection__id=self.value())


class ArticleSourceCollectionFilter(SimpleListFilter):
    title = _("Collection")
    parameter_name = "collection"

    def lookups(self, request, model_admin):
        collections = Collection.objects.filter(is_active=True)
        return [(collection.id, collection.main_name) for collection in collections]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(am_article__collection__id=self.value())


class ArticleCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ArticleAdmin(ModelAdmin):
    model = Article
    create_view_class = ArticleCreateView
    menu_label = _("Article")
    menu_icon = "folder"
    menu_order = 1
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_per_page = 20
    list_display = (
        "sps_pkg_name",
        "pid_v3",
        "pid_v2",
        "is_public",
        "valid",
        "data_status",
        "created",
        "updated",
    )
    list_filter = ("is_public", "data_status", "valid", CollectionFilter)
    search_fields = (
        "titles__plain_text",
        "pid_v2",
        "doi__value",
        "sps_pkg_name",
        "pid_v3",
    )


class ArticleExporterCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ArticleExporterAdmin(ModelAdmin):
    model = ArticleExporter
    create_view_class = ArticleExporterCreateView
    menu_label = _("Article Export")
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = ("parent", "collection", "destination", "status", "updated")
    list_filter = (
        "collection",
        "destination",
        "status",
    )
    search_fields = ("parent__pid_v3", "parent__sps_pkg_name")

    def pid_v3(self, obj):
        return obj.parent.pid_v3

    pid_v3.short_description = "PID_V3"


class ArticleFormatCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ArticleFormatAdmin(ModelAdmin):
    model = ArticleFormat
    create_view_class = ArticleFormatCreateView
    menu_label = _("Article Format")
    menu_icon = "folder"
    menu_order = 500
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

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


class ArticleFundingCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ArticleFundingAdmin(ModelAdmin):
    model = ArticleFunding
    create_view_class = ArticleFundingCreateView
    menu_label = _("Article Funding")
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    list_display = ("award_id", "funding_source")
    search_fields = (
        "award_id",
        "funding_source__name",
        "funding_source__institution_type",
    )


class ArticleAdminGroup(ModelAdminGroup):
    menu_label = _("Articles")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = get_menu_order(
        "article"
    )  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (
        ArticleAdmin,
        # ArticleAvailabilitySnippetViewSet,
        ArticleExporterAdmin,
        ArticleFormatAdmin,
        ArticleFundingAdmin,
    )


modeladmin_register(ArticleAdminGroup)


class DuplicateArticlesViewSet(SnippetViewSet):
    model = Article
    icon = "folder"
    list_display = ["pid_v3", "updated", "created"]

    def get_queryset(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied
        ids_duplicates = []
        duplicates = (
            Article.objects.all()
            .values("pid_v3")
            .annotate(pid_v3_count=Count("pid_v3"))
            .filter(pid_v3_count__gt=1)
        )

        for duplicate in duplicates:
            article_ids = (
                Article.objects.filter(pid_v3=duplicate["pid_v3"])
                .order_by("created")[1:]
                .values_list("id", flat=True)
            )
            ids_duplicates.extend(article_ids)

        if ids_duplicates:
            return Article.objects.filter(id__in=ids_duplicates)
        else:
            return Article.objects.none()


register_snippet(DuplicateArticlesViewSet)


class ArticleSourceSnippetViewSet(SnippetViewSet):
    """Custom ViewSet for ArticleSource snippets"""

    model = ArticleSource
    menu_label = _("Article Sources")
    menu_icon = "doc-full"
    menu_order = 200

    # List view configuration
    list_display = ["am_article", "pid_provider_xml", "status", "source_date", "updated"]
    list_filter = ["status", "am_article__collection",]
    search_fields = ["url", "pid_provider_xml__v3", "am_article__collection__acronym"]
    ordering = ["-updated"]
    list_per_page = 25


# Register the snippet
register_snippet(ArticleSourceSnippetViewSet)
