from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from wagtail.contrib.modeladmin.views import CreateView

from .models import XMLSPS


class XMLSPSCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class XMLSPSAdmin(ModelAdmin):
    list_per_page = 100
    model = XMLSPS
    inspect_view_enabled = True
    menu_label = _("XMLSPS")
    create_view_class = XMLSPSCreateView
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "is_published",
        "pid_v3",
    )
    list_filter = ("is_published",)
    search_fields = (
        "pid_v3",
        "pid_v2",
        "aop_pid",
        "xml_issue__pub_year",
    )


modeladmin_register(XMLSPSAdmin)
