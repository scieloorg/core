from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from .models import (
    PidProviderConfig,
    CollectionPidRequest,
    OtherPid,
    PidProviderXML,
    PidRequest,
)


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
        "v3",
        "times",
        "created",
        "updated",
    )
    list_filter = ("result_type",)
    search_fields = (
        "origin",
        "v3",
        "result_msg",
    )


class CollectionPidRequestAdmin(ModelAdmin):
    list_per_page = 10
    model = CollectionPidRequest
    inspect_view_enabled = True
    menu_label = _("Collection Pid Requests")
    create_view_class = PidRequestCreateView
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "collection",
        "end_date",
        "created",
        "updated",
    )
    list_filter = []
    search_fields = (
        "collection__acron3",
        "collection__name",
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
        "available_since",
        "other_pid_count",
        "created",
        "updated",
    )
    list_filter = (
        "article_pub_year",
        "pub_year",
        "other_pid_count",
    )
    search_fields = (
        "pkg_name",
        "v3",
        "v2",
        "aop_pid",
        "main_doi",
        "article_pub_year",
        "available_since",
    )


class OtherPidAdminCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class OtherPidAdmin(ModelAdmin):
    list_per_page = 10
    model = OtherPid
    inspect_view_enabled = True
    menu_label = _("Pid Changes")
    create_view_class = OtherPidAdminCreateView
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "pid_provider_xml",
        "pid_in_xml",
        "pid_type",
        "created",
        "updated",
    )
    list_filter = ("pid_type",)
    search_fields = (
        "pid_in_xml",
        "pid_provider_xml__v3",
    )


class PidProviderConfigCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class PidProviderConfigAdmin(ModelAdmin):
    list_per_page = 10
    model = PidProviderConfig
    inspect_view_enabled = True
    menu_label = _("Pid Provider Config")
    create_view_class = PidProviderConfigCreateView
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "pid_provider_api_post_xml",
        "pid_provider_api_get_token",
    )


class PidProviderAdminGroup(ModelAdminGroup):
    menu_label = _("Pid Provider")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = 6
    items = (
        PidProviderConfigAdmin,
        PidProviderXMLAdmin,
        PidRequestAdmin,
        OtherPidAdmin,
        CollectionPidRequestAdmin,
    )


modeladmin_register(PidProviderAdminGroup)
