from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from .models import PidRequest, PidProviderXML, PidChange


class PidRequestCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class PidRequestAdmin(ModelAdmin):
    list_per_page = 10
    model = PidRequest
    inspect_view_enabled = True
    menu_label = _("Pid Requests")
    create_view_class = PidRequestCreateView
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "origin",
        "result_type",
        "result_msg",
        "created",
    )
    list_filter = ("result_type",)
    search_fields = (
        "origin",
        "result_msg",
    )


class PidProviderXMLAdminCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class PidProviderXMLAdmin(ModelAdmin):
    list_per_page = 10
    model = PidProviderXML
    inspect_view_enabled = True
    menu_label = _("Pid Provider XMLs")
    create_view_class = PidProviderXMLAdminCreateView
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "pkg_name",
        "v3",
        "v2",
        "aop_pid",
        "main_doi",
    )
    list_filter = ("article_pub_year",)
    search_fields = (
        "pkg_name",
        "v3",
        "v2",
        "aop_pid",
        "main_doi",
        "article_pub_year",
    )


class PidChangeAdminCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class PidChangeAdmin(ModelAdmin):
    list_per_page = 10
    model = PidChange
    inspect_view_enabled = True
    menu_label = _("Pid Changes")
    create_view_class = PidChangeAdminCreateView
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "pkg_name",
        "pid_in_xml",
        "pid_assigned",
        "pid_type",
    )
    list_filter = ("pid_type",)
    search_fields = (
        "pid_in_xml",
        "pid_assigned",
    )


class PidProviderAdminGroup(ModelAdminGroup):
    menu_label = _("Pid Provider")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (PidProviderXMLAdmin, PidRequestAdmin, PidChangeAdmin)


modeladmin_register(PidProviderAdminGroup)
