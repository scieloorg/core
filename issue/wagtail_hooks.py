from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail_modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail_modeladmin.views import CreateView

from .models import Issue, IssueExport
from config.menu import get_menu_order


class IssueCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class IssueAdmin(ModelAdmin):
    model = Issue
    inspect_view_enabled = True
    menu_label = _("Issues")
    create_view_class = IssueCreateView
    menu_icon = "folder-open-inverse"
    menu_order = 150
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "journal",
        "year",        
        "volume",        
        "number",
        "supplement",
        "created",
        "updated",
    )
    list_filter = (
        "year",
        "month",
    )
    search_fields = (
        "journal__title",
        "journal__official__issn_print",
        "journal__official__issn_electronic",
        "number",
        "volume",
        "year",
        "month",
        "supplement",
    )


class IssueExportCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class IssueExportAdmin(ModelAdmin):
    model = IssueExport
    create_view_class = IssueExportCreateView
    inspect_view_enabled = True
    menu_label = _("Issue Exports")
    menu_icon = "download"
    menu_order = 160
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "issue",
        "export_type",
        "collection",
        "created",
        "updated",
    )
    list_filter = (
        "export_type",
        "collection",
    )
    search_fields = (
        "issue__journal__title",
        "issue__number",
        "issue__volume",
        "issue__year",
    )


class IssueAdminGroup(ModelAdminGroup):
    menu_label = _("Issues")
    menu_icon = "folder-open-inverse"
    menu_order = get_menu_order("issue")
    items = (IssueAdmin, IssueExportAdmin)


modeladmin_register(IssueAdminGroup)
