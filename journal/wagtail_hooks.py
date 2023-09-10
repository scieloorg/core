from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView
from wagtail import hooks
from django.urls import path

from .models import Journal, OfficialJournal, SciELOJournal, IndexedAt, IndexedAtFile
from .button_helper import IndexedAtHelper
from .views import import_file, validate


class OfficialJournalCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class OfficialJournalAdmin(ModelAdmin):
    model = OfficialJournal
    inspect_view_enabled = True
    menu_label = _("Official Journals")
    create_view_class = OfficialJournalCreateView
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "title",
        "foundation_year",
        "issn_print",
        "issn_electronic",
        "issnl",
    )
    list_filter = ("foundation_year",)
    search_fields = (
        "foundation_year",
        "issn_print",
        "issn_electronic",
        "issnl",
        "creator",
        "updated_by",
    )


class JournalCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class JournalAdmin(ModelAdmin):
    model = Journal
    inspect_view_enabled = True
    menu_label = _("Journals")
    create_view_class = JournalCreateView
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "official",
        "title",
        "short_title",
    )
    # list_filter = ()
    search_fields = (
        "title",
        "official__issn_print",
        "official__issn_electronic",
    )


class SciELOJournalCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class SciELOJournalAdmin(ModelAdmin):
    model = SciELOJournal
    inspect_view_enabled = True
    menu_label = _("SciELO Journals")
    create_view_class = SciELOJournalCreateView
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "collection",
        "issn_scielo",
        "journal_acron",
        "journal",
    )
    search_fields = (
        "journal_acron",
        "issn_scielo",
    )


class JournalAdminGroup(ModelAdminGroup):
    menu_label = _("Journals")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (JournalAdmin, OfficialJournalAdmin, SciELOJournalAdmin)


modeladmin_register(JournalAdminGroup)


class IndexedAtAdmin(ModelAdmin):
    model = IndexedAt
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


class IndexedAtFileAdmin(ModelAdmin):
    model = IndexedAtFile
    button_helper_class = IndexedAtHelper
    menu_label = "Indexed At Upload"
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ("attachment", "line_count", "is_valid")
    list_filter = ("is_valid",)
    search_fields = ("attachment",)


class IndexedAtAdminGroup(ModelAdminGroup):
    menu_label = "Indexed At"
    menu_icon = "folder-open-inverse"
    menu_order = 200
    items = (
        IndexedAtAdmin,
        IndexedAtFileAdmin,
    )


modeladmin_register(IndexedAtAdminGroup)


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