from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from .models import PidProviderBadRequest


class PidProviderBadRequestCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class PidProviderBadRequestAdmin(ModelAdmin):
    model = PidProviderBadRequest
    inspect_view_enabled = True
    menu_label = _("PidProviderBadRequests")
    create_view_class = PidProviderBadRequestCreateView
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "basename",
        "error_type",
        "error_message",
    )
    list_filter = (
        "creator",
        "error_type",
    )
    search_fields = (
        "basename",
        "error_message",
    )


modeladmin_register(PidProviderBadRequestAdmin)
