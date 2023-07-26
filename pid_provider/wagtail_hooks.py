from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from .models import PidRequest


class PidRequestCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class PidRequestAdmin(ModelAdmin):
    model = PidRequest
    inspect_view_enabled = True
    menu_label = _("PidRequests")
    create_view_class = PidRequestCreateView
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "collection_acron",
        "origin",
        "pid_v3",
        "pid_v2",
        "pkg_name",
        "result_type",
        "result_msg",
        "created",
    )
    list_filter = (
        "collection_acron",
        "origin",
        "result_type",
    )
    search_fields = (
        "collection_acron",
        "origin",
        "pid_v3",
        "pid_v2",
        "pkg_name",
        "result_msg",
    )


modeladmin_register(PidRequestAdmin)
