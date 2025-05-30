from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.translation import gettext as _
from wagtail import hooks
from wagtail.snippets import widgets as wagtailsnippets_widgets
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import (
    CreateView,
    SnippetViewSet,
    SnippetViewSetGroup,
)
from wagtail_modeladmin.options import ModelAdmin
from wagtail_modeladmin.views import CreateView, EditView

from config.menu import get_menu_order
from journalpage.models import JournalPage

from . import models
from .button_helper import IndexedAtHelper
from .views import import_file, validate

COLLECTION_TEAM = "Collection Team"
JOURNAL_TEAM = "Journal Team"


class OfficialJournalCreateViewSnippet(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class OfficialJournalSnippetViewSet(SnippetViewSet):
    model = models.OfficialJournal
    menu_label = _("ISSN Journals")
    add_view_class = OfficialJournalCreateViewSnippet
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False
    exclude_from_explorer = False
    add_to_admin_menu = True
    list_display = (
        "title",
        "initial_year",
        "terminate_year",
        "issn_print",
        "issn_print_is_active",
        "issn_electronic",
        "created",
        "updated",
    )
    list_filter = (
        "issn_print_is_active",
        "terminate_year",
        "initial_year",
    )
    search_fields = (
        "title",
        "initial_year",
        "issn_print",
        "issn_electronic",
        "issnl",
    )


class JournalCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class JournalAdminSnippetViewSet(SnippetViewSet):
    model = models.Journal
    inspect_view_enabled = True
    menu_label = _("Journals")
    add_view_class = JournalCreateView
    menu_icon = "folder"
    menu_order = get_menu_order("journal")
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_per_page = 20

    list_display = (
        "title",
        "contact_location",
        "created",
        "updated",
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
            models.Journal.objects.all()
            .select_related("contact_location")
            .prefetch_related("scielojournal_set")
        )
        user_groups = request.user.groups.values_list("name", flat=True)
        if COLLECTION_TEAM in user_groups:
            return qs.filter(
                scielojournal__collection__in=request.user.collection.all()
            )
        elif JOURNAL_TEAM in user_groups:
            return qs.filter(
                id__in=request.user.journal.all().values_list("id", flat=True)
            )
        return qs


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
        qs = models.SciELOJournal.objects.all().select_related("journal", "collection")
        user_groups = request.user.groups.values_list("name", flat=True)
        if COLLECTION_TEAM in user_groups:
            return qs.filter(collection__in=request.user.collection.all())
        elif JOURNAL_TEAM in user_groups:
            return qs.filter(
                id__in=request.user.journal.all().values_list("id", flat=True)
            )
        return qs


class JournalSnippetViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Journals")
    menu_icon = "folder-open-inverse"
    menu_order = get_menu_order("journal")
    items = (
        JournalAdminSnippetViewSet,
        OfficialJournalSnippetViewSet,
        SciELOJournalAdminViewSet,
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


# TODO
# Futuramente mudar para JournalAdminGroup
# com permissoes de visualizacao restrita
class AMJournalAdmin(ModelAdmin):
    model = models.AMJournal
    menu_label = "AM Journal"
    menu_icon = "folder"
    menu_order = get_menu_order("amjournal")
    list_display = ("scielo_issn", "collection")
    list_filter = ("collection",)
    search_fields = ("scielo_issn",)


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


@hooks.register('register_snippet_listing_buttons')
def snippet_listing_buttons(snippet, user, next_url=None):
    if isinstance(snippet, models.Journal):
        journal_page = JournalPage.objects.get(slug="journal")
        scielo_journal = models.SciELOJournal.objects \
            .only("collection__acron3", "journal_acron") \
            .select_related("collection") \
            .filter(journal=snippet, collection__is_active=True).first()
        url = journal_page.get_url() + journal_page.reverse_subpage('bibliographic', args=[scielo_journal.collection.acron3, scielo_journal.journal_acron])
        yield wagtailsnippets_widgets.SnippetListingButton(
            _(f'Preview about journal'), 
            url,
            priority=1,
            icon_name='view',
            attrs={"target": "_blank"},
        )