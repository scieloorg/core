from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from .models import Issue
from core.wagtail_hooks import BaseEditView

class IssueCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())

class IssueEditView(BaseEditView):
    readonly_fields = [
        "journal"
    ]

class IssueAdmin(ModelAdmin):
    model = Issue
    inspect_view_enabled = True
    menu_label = _("Issues")
    create_view_class = IssueCreateView
    edit_view_class = IssueEditView
    menu_icon = "folder-open-inverse"
    menu_order = 3
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "journal",
        "number",
        "volume",
        "year",
        "month",
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
    )


class IssueAdminGroup(ModelAdminGroup):
    menu_label = _("Issues")
    menu_icon = "folder-open-inverse"
    menu_order = 100
    items = (IssueAdmin, )


modeladmin_register(IssueAdminGroup)
