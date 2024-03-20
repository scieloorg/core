from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.translation import gettext as _
from wagtail import hooks
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from . import models
from .button_helper import IndexedAtHelper
from .views import import_file, validate
from config.menu import get_menu_order

COLLECTION_TEAM = "Collection Team"
JOURNAL_TEAM = "Journal Team"


class OfficialJournalCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class OfficialJournalAdmin(ModelAdmin):
    model = models.OfficialJournal
    inspect_view_enabled = True
    menu_label = _("ISSN Journals")
    create_view_class = OfficialJournalCreateView
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False
    exclude_from_explorer = False

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
    list_filter = ("issn_print_is_active", "terminate_year", "initial_year", )
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


class JournalAdmin(ModelAdmin):
    model = models.Journal
    inspect_view_enabled = True
    menu_label = _("Journals")
    create_view_class = JournalCreateView
    menu_icon = "folder"
    menu_order = get_menu_order("journal")
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_per_page = 20

    list_display = (
        "title",
        "contact_location",
        "valid",
        "created",
        "updated",
    )
    list_filter = (
        "valid",
        "use_license",
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
        qs = super().get_queryset(request)
        user_groups = request.user.groups.values_list('name', flat=True)
        if COLLECTION_TEAM in user_groups:
            return qs.filter(scielojournal__collection__in=request.user.collection.all())
        elif JOURNAL_TEAM in user_groups:
            return qs.filter(id__in=request.user.journal.all().values_list("id", flat=True))
        return qs
    

class SciELOJournalCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class SciELOJournalAdmin(ModelAdmin):
    model = models.SciELOJournal
    inspect_view_enabled = True
    menu_label = _("SciELO Journals")
    create_view_class = SciELOJournalCreateView
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "journal",
        "issn_scielo",
        "journal_acron",
        "collection",
        "status",
        "created",
        "updated",
    )
    list_filter = ("status", "collection", )
    search_fields = (
        "journal_acron",
        "journal__title",
        "issn_scielo",
    )
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user_groups = request.user.groups.values_list('name', flat=True)
        if COLLECTION_TEAM in user_groups:
            return qs.filter(collection__in=request.user.collection.all())
        elif JOURNAL_TEAM in user_groups:
            return qs.filter(id__in=request.user.journal.all().values_list("id", flat=True))
        return qs




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
    list_display = (
        "name",
    )
    search_fields = (
        "name",
    )


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

modeladmin_register(AMJournalAdmin)
# modeladmin_register(ArticleSubmissionFormatCheckListAdmin)


class JournalAdminGroup(ModelAdminGroup):
    menu_label = _("Journals")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = get_menu_order("journal")
    items = (JournalAdmin, OfficialJournalAdmin, SciELOJournalAdmin, AMJournalAdmin)


modeladmin_register(JournalAdminGroup)


class OwnerAdmin(ModelAdmin):
    model = models.Owner
    menu_icon = "folder"
    menu_order = 300
    menu_label = _("Owner")
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = ("institution",)
    search_fields = (
        "institution__institution_identification__name",
        "institution__institution_identification__acronym",
        "institution__level_1",
        "institution__level_2",
        "institution__level_3",
    )
    list_export = (
        "institution__institution_identification__name",
        "institution__institution_identification__acronym",
        "institution__level_1",
        "institution__level_2",
        "institution__level_3",
        "location",
    )
    export_filename = "owner"


class CopyrightholderAdmin(ModelAdmin):
    model = models.CopyrightHolder
    menu_icon = "folder"
    menu_order = 400
    menu_label = _("Copyrightholder")
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = ("institution",)
    search_fields = (
        "institution__institution_identification__name",
        "institution__institution_identification__acronym",
        "institution__level_1",
        "institution__level_2",
        "institution__level_3",
    )
    list_export = (
        "institution__institution_identification__name",
        "institution__institution_identification__acronym",
        "institution__level_1",
        "institution__level_2",
        "institution__level_3",
        "location",
    )
    export_filename = "copyrightholder"


class PublisherAdmin(ModelAdmin):
    model = models.Publisher
    menu_icon = "folder"
    menu_order = 500
    menu_label = _("Publisher")
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = ("institution",)
    search_fields = (
        "institution__institution_identification__name",
        "institution__institution_identification__acronym",
        "institution__level_1",
        "institution__level_2",
        "institution__level_3",
    )
    list_export = (
        "institution__institution_identification__name",
        "institution__institution_identification__acronym",
        "institution__level_1",
        "institution__level_2",
        "institution__level_3",
        "location",
    )
    export_filename = "Publisher"


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
