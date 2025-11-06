from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.snippets import widgets as wagtailsnippets_widgets
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import (
    CreateView,
    SnippetViewSet,
    SnippetViewSetGroup,
)
from wagtail_modeladmin.options import ModelAdmin

from config.menu import get_menu_order
from journalpage.models import JournalPage

from . import models
from .button_helper import IndexedAtHelper
from .proxys import (
    JournalProxyEditor,
    JournalProxyPanelInstructionsForAuthors,
    JournalProxyPanelPolicy,
)
from .views import import_file, validate


class OfficialJournalCreateViewSnippet(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class OfficialJournalSnippetViewSet(SnippetViewSet):
    model = models.OfficialJournal
    menu_label = _("Journals (ISSN)")
    inspect_view_enabled = True
    add_view_class = OfficialJournalCreateViewSnippet
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "title",
        "initial_year",
        "issn_print",
        "issn_print_is_active",
        "issn_electronic",
        "updated",
    )
    list_filter = (
        "issn_print_is_active",
        "terminate_year",
        "country",
    )
    search_fields = (
        "title",
        "issn_print",
        "issn_electronic",
        "issnl",
    )


class JournalExporterCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class JournalExporterSnippetViewSet(SnippetViewSet):
    model = models.JournalExporter
    inspect_view_enabled = True
    add_view_class = JournalExporterCreateView
    menu_label = _("Journal Exporter")
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "parent",
        "pid",
        "status",
        "collection",
        "destination",
        "updated",
    )
    list_filter = (
        "collection",
        "destination",
        "status",
    )
    search_fields = (
        "parent__title",
        "pid",
    )


class JournalCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class FilteredJournalQuerysetMixin:
    """
    Mixin que filtra o queryset de journals baseado nas permissões
    e grupos do usuário (COLLECTION_TEAM ou JOURNAL_TEAM).
    """

    list_display = (
        "title",
        "contact_location",
        "created",
        "updated",
        "creator",
        "updated_by",
    )
    list_filter = (
        "journal_use_license",
        "publishing_model",
        "subject",
        "main_collection",
    )
    search_fields = (
        "title",
        "official__issn_print",
        "official__issn_electronic",
        "contact_location__country__name",
    )

    def get_queryset(self, request):
        qs = (
            models.Journal.objects
            .select_related("contact_location")
            .prefetch_related("scielojournal_set")
        )
        user = request.user
        if not user.is_authenticated:
            return qs.none()

        if user.is_superuser:
            return qs.all()

        if user.has_collection_permission and user.collection_ids:
            return qs.filter(
                scielojournal__collection__in=user.collection_ids
            ).distinct()
        elif user.has_journal_permission and user.journal_ids:
            return qs.filter(
                scielojournal__journal__id__in=user.journal_ids
            ).distinct()
        return qs.none()


class JournalAdminSnippetViewSet(FilteredJournalQuerysetMixin, SnippetViewSet):
    model = models.Journal
    inspect_view_enabled = True
    menu_label = _("Journals (admin)")
    add_view_class = JournalCreateView
    menu_icon = "folder"
    menu_order = get_menu_order("journal")
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_per_page = 20


class JournalAdminEditorSnippetViewSet(FilteredJournalQuerysetMixin, SnippetViewSet):
    model = JournalProxyEditor
    inspect_view_enabled = True
    menu_label = _("Journals")
    menu_icon = "folder"
    menu_order = get_menu_order("journal")
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_per_page = 20


class JournalAdminPolicySnippetViewSet(FilteredJournalQuerysetMixin, SnippetViewSet):
    model = JournalProxyPanelPolicy
    inspect_view_enabled = True
    menu_label = _("Journal Policies")
    menu_icon = "folder"
    menu_order = get_menu_order("journal")
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_per_page = 20


class JournalAdminInstructionsForAuthorsSnippetViewSet(
    FilteredJournalQuerysetMixin, SnippetViewSet
):
    model = JournalProxyPanelInstructionsForAuthors
    inspect_view_enabled = True
    menu_label = _("Journal Instructions for Authors")
    menu_icon = "folder"
    menu_order = get_menu_order("journal")
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_per_page = 20


class SciELOJournalCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class SciELOJournalAdminViewSet(SnippetViewSet):

    model = models.SciELOJournal
    inspect_view_enabled = True
    menu_label = _("SciELO Journals")
    add_view_class = SciELOJournalCreateView
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "journal__title",
        "journal__official__initial_year",
        "issn_scielo",
        "journal_acron",
        "collection",
        "status",
        "created",
        "updated",
    )
    list_filter = (
        "status",
        "collection",
    )
    search_fields = (
        "journal_acron",
        "journal__title",
        "issn_scielo",
    )

    def get_queryset(self, request):
        user = request.user
        if user.is_superuser:
            return models.SciELOJournal.objects.select_related("journal", "collection")

        if user.journal_ids:
            return models.SciELOJournal.objects.filter(
                journal__in=user.journal_ids
            ).select_related("journal", "collection")
        
        if user.collection_ids:
            return models.SciELOJournal.objects.filter(
                collection__in=user.collection_ids
            ).select_related("journal", "collection")
        
        return models.SciELOJournal.objects.none()


class AMJournalAdmin(SnippetViewSet):
    model = models.AMJournal
    menu_label = "AM Journal"
    menu_icon = "folder"
    menu_order = get_menu_order("amjournal")
    list_display = ("pid", "collection", "processing_date", "status")
    list_filter = ("collection", "status")
    search_fields = ("pid",)


class JournalSnippetViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Journals")
    menu_icon = "folder-open-inverse"
    menu_order = get_menu_order("journal")
    items = (
        OfficialJournalSnippetViewSet,
        JournalAdminSnippetViewSet,
        SciELOJournalAdminViewSet,
        JournalAdminEditorSnippetViewSet,
        JournalExporterSnippetViewSet,
        JournalAdminPolicySnippetViewSet,
        JournalAdminInstructionsForAuthorsSnippetViewSet,
        AMJournalAdmin,
    )


register_snippet(JournalSnippetViewSetGroup)


class TOCSectionAdmin(ModelAdmin):
    model = models.JournalTocSection
    menu_label = "Table of Contents"
    menu_icon = "folder"
    menu_order = 500
    search_fields = (
        "journal__title",
        "journal__official__issn_print",
        "journal__official__issn_electronic",
        "journal__contact_location__country__name",
    )
    list_display = ("journal", "column_toc")

    def column_toc(self, obj):
        return str(obj)

    column_toc.short_description = "Table of Contents"


class IndexedAtAdmin(ModelAdmin):
    model = models.IndexedAt
    menu_label = "Indexed At"
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ("name", "acronym", "url", "description", "type")
    list_filter = ("type",)
    search_fields = ("name", "acronym")
    list_export = ("name", "acronym", "url", "description", "type")
    export_filename = "indexed_at"


class AdditionalIndexedAtAdmin(ModelAdmin):
    model = models.AdditionalIndexedAt
    menu_label = "Additional Indexed At"
    menu_icon = "folder"
    menu_order = 110
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ("name",)
    search_fields = ("name",)


class IndexedAtFileAdmin(ModelAdmin):
    model = models.IndexedAtFile
    button_helper_class = IndexedAtHelper
    menu_label = "Indexed At Upload"
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ("attachment", "line_count", "is_valid")
    list_filter = ("is_valid",)
    search_fields = ("attachment",)


class WebOfKnowledgeAdmin(ModelAdmin):
    model = models.WebOfKnowledge
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "code",
        "value",
    )

    search_fields = (
        "code",
        "value",
    )


class SubjectAdmin(ModelAdmin):
    model = models.Subject
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "code",
        "value",
    )

    search_fields = (
        "code",
        "value",
    )


class WosAreaAdmin(ModelAdmin):
    model = models.WebOfKnowledgeSubjectCategory
    menu_icon = "folder"
    menu_order = 400
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ("value",)
    search_fields = ("value",)


class StandardAdmin(ModelAdmin):
    model = models.Standard
    menu_icon = "folder"
    menu_order = 500
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "code",
        "value",
    )

    search_fields = (
        "code",
        "value",
    )


class ArticleSubmissionFormatCheckListAdmin(ModelAdmin):
    model = models.ArticleSubmissionFormatCheckList
    menu_label = _("Article Submission Format Check List")
    menu_icon = "folder"
    menu_order = get_menu_order("article_subm")


# modeladmin_register(ArticleSubmissionFormatCheckListAdmin)


@hooks.register("register_admin_urls")
def register_calendar_url():
    return [
        path(
            "controlled_lists/indexedatfile/validate",
            validate,
            name="validate",
        ),
        path(
            "controlled_lists/indexedatfile/import_file",
            import_file,
            name="import_file",
        ),
    ]


@hooks.register("register_snippet_listing_buttons")
def snippet_listing_buttons(snippet, user, next_url=None):
    if isinstance(snippet, models.Journal):
        journal_page = JournalPage.objects.filter(slug="journal").first()
        scielo_journal = (
            models.SciELOJournal.objects.only("collection__acron3", "journal_acron")
            .select_related("collection")
            .filter(journal=snippet)
            .first()
        )
        try:
            url = journal_page.get_url() + journal_page.reverse_subpage(
                "bibliographic",
                args=[scielo_journal.collection.acron3, scielo_journal.journal_acron],
            )
            yield wagtailsnippets_widgets.SnippetListingButton(
                _(f"Preview about journal"),
                url,
                priority=1,
                icon_name="view",
                attrs={"target": "_blank"},
            )
        except AttributeError:
            pass


@hooks.register("register_permissions")
def register_ctf_permissions():
    model = JournalProxyEditor
    content_type = ContentType.objects.get_for_model(model, for_concrete_model=False)
    return Permission.objects.filter(content_type=content_type)


@hooks.register("register_permissions")
def register_ctf_permissions_1():
    model = JournalProxyPanelPolicy
    content_type = ContentType.objects.get_for_model(model, for_concrete_model=False)
    return Permission.objects.filter(content_type=content_type)


@hooks.register("register_permissions")
def register_ctf_permissions_2():
    model = JournalProxyPanelInstructionsForAuthors
    content_type = ContentType.objects.get_for_model(model, for_concrete_model=False)
    return Permission.objects.filter(content_type=content_type)
