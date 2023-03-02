from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from .models import OfficialJournal, ScieloJournal


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


class ScieloJournalCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ScieloJournalAdmin(ModelAdmin):
    model = ScieloJournal
    inspect_view_enabled = True
    menu_label = _("SciELO Journals")
    create_view_class = ScieloJournalCreateView
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "official",
        "issn_scielo",
        "title",
        "short_title",
    )
    # list_filter = ()
    search_fields = ("official",)


class JournalAdminGroup(ModelAdminGroup):
    menu_label = _("Journals")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (OfficialJournalAdmin, ScieloJournalAdmin)


modeladmin_register(JournalAdminGroup)
