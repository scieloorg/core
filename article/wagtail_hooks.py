from typing import Any

from django.contrib.admin import SimpleListFilter
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.db.models.query import QuerySet
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail_modeladmin.options import ModelAdmin, ModelAdminGroup, modeladmin_register
from wagtail_modeladmin.views import CreateView

from article.models import (  # AbstractModel,; Category,; Title,
    Article,
    ArticleExport,
    ArticleFormat,
    ArticleFunding,
    ArticleSource,
)
from collection.models import Collection
from config.menu import get_menu_order


class CollectionFilter(SimpleListFilter):
    title = _("Collection")
    parameter_name = "collection"

    def lookups(self, request, model_admin):
        collections = Collection.objects.filter(is_active=True)
        return [(collection.id, collection.main_name) for collection in collections]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(journal__scielojournal__collection__id=self.value())


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
        "valid",
        "data_status",
        "created",
        "updated",
    )
    list_filter = ("valid", CollectionFilter, "data_status")
    search_fields = (
        "titles__plain_text",
        "pid_v2",
        "doi__value",
        "sps_pkg_name",
        "pid_v3",
    )


class ArticleExportCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())
    

class ArticleExportAdmin(ModelAdmin):
    model = ArticleExport
    create_view_class = ArticleExportCreateView
    menu_label = _("Article Export")
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False
    exclude_from_explorer = (False)

    list_display = (
        "article",
        "pid_v3", 
        "export_type", 
        "created", 
        "updated"
    )
    list_filter = (
        "collection", 
        "export_type",
    )
    search_fields = (
        "article__pid_v3", 
        "article__sps_pkg_name"
    )

    def pid_v3(self, obj):
        return obj.article.pid_v3
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
    items = (ArticleAdmin, ArticleExportAdmin, ArticleFormatAdmin, ArticleFundingAdmin)


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
    list_display = ["__str__", "status", "source_date", "article", "updated"]
    list_filter = ["status", "source_date", "created", "updated"]
    search_fields = ["url", "file"]
    ordering = ["-updated"]
    list_per_page = 25

    # Form configuration
    form_fields_exclude = []

    # Custom actions
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        if qs:
            return qs.select_related("article", "pid_provider_xml")


# Register the snippet
register_snippet(ArticleSourceSnippetViewSet)
