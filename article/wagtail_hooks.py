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
    items = (ArticleAdmin, ArticleFormatAdmin, ArticleFundingAdmin)


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

    # Custom bulk actions
    def get_bulk_actions(self):
        """Add custom bulk actions"""
        bulk_actions = super().get_bulk_actions()
        bulk_actions.update(
            {
                "reprocess": self.bulk_reprocess,
                "reset_pending": self.bulk_reset_pending,
            }
        )
        return bulk_actions

    def bulk_reprocess(self, request, queryset):
        """Bulk reprocess action"""
        count = queryset.update(status=ArticleSource.StatusChoices.REPROCESS)
        messages.success(request, f"{count} article sources marked for reprocessing.")
        return HttpResponseRedirect(request.get_full_path())

    bulk_reprocess.short_description = _("Mark selected for reprocessing")

    def bulk_reset_pending(self, request, queryset):
        """Bulk reset to pending action"""
        count = queryset.update(status=ArticleSource.StatusChoices.PENDING)
        messages.success(request, f"{count} article sources reset to pending.")
        return HttpResponseRedirect(request.get_full_path())

    bulk_reset_pending.short_description = _("Reset selected to pending")

    # Custom views
    def get_admin_urls_for_registration(self):
        """Add custom URLs"""
        urls = super().get_admin_urls_for_registration()
        custom_urls = [
            path(
                "<str:pk>/reprocess/",
                self.reprocess_view,
                name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_reprocess",
            ),
            path(
                "bulk-actions/",
                self.bulk_actions_view,
                name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_bulk_actions",
            ),
        ]
        return urls + custom_urls

    def reprocess_view(self, request, pk):
        """Individual reprocess view"""
        try:
            obj = self.model.objects.get(pk=pk)
            obj.status = ArticleSource.StatusChoices.REPROCESS
            obj.save()
            messages.success(request, f"Article source marked for reprocessing: {obj}")
        except self.model.DoesNotExist:
            messages.error(request, "Article source not found.")

        return redirect(self.index_url_name)

    def bulk_actions_view(self, request):
        """Handle bulk actions"""
        if request.method == "POST":
            action = request.POST.get("action")
            selected_ids = request.POST.getlist("selected_items")

            if not selected_ids:
                messages.warning(request, "No items selected.")
                return redirect(self.index_url_name)

            queryset = self.model.objects.filter(pk__in=selected_ids)

            if action == "reprocess":
                return self.bulk_reprocess(request, queryset)
            elif action == "reset_pending":
                return self.bulk_reset_pending(request, queryset)

        return redirect(self.index_url_name)


# Register the snippet
register_snippet(ArticleSource, viewset=ArticleSourceSnippetViewSet)
