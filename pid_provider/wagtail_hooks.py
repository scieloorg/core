from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSetGroup

from config.menu import get_menu_order
from core.viewsets import CommonControlFieldViewSet
from pid_provider.models import FixPidV2, OtherPid, PidProviderConfig, PidProviderXML


class PidProviderXMLViewSet(CommonControlFieldViewSet):
    model = PidProviderXML
    menu_label = _("Pid Provider XMLs")
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    list_per_page = 10

    # Configuração de listagem
    list_display = [
        "pkg_name",
        "collection_list",
        "v3",
        "v2",
        "aop_pid",
        "main_doi",
        "available_since",
        "other_pid_count",
        "updated",
    ]
    list_filter = {
        "proc_status": ["exact"],
        "collections": ["exact"],
        "pub_year": ["exact", "gte", "lte"],
        "other_pid_count": ["exact", "gte", "lte"],
        "registered_in_core": ["exact"],
    }
    search_fields = (
        "pkg_name",
        "v3",
        "v2",
        "aop_pid",
        "main_doi",
        "pub_year",
        "available_since",
    )

    # Configuração de export
    list_export = [
        "pkg_name",
        "proc_status",
        "v3",
        "v2",
        "aop_pid",
        "main_doi",
        "pub_year",
        "available_since",
        "other_pid_count",
        "registered_in_core",
    ]
    export_filename = "pid_provider_xmls"


class OtherPidViewSet(CommonControlFieldViewSet):
    model = OtherPid
    menu_label = _("Pid Changes")
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    list_per_page = 10

    # Configuração de listagem
    list_display = [
        "pid_provider_xml",
        "pid_in_xml",
        "pid_type",
        "created",
        "updated",
    ]
    list_filter = {
        "pid_type": ["exact"],
    }
    search_fields = ("pid_in_xml", "pid_provider_xml__v3", "pid_provider_xml__pkg_name")

    # Configuração de export
    list_export = [
        "pid_provider_xml",
        "pid_in_xml",
        "pid_type",
        "created",
        "updated",
    ]
    export_filename = "other_pids"


class PidProviderConfigViewSet(CommonControlFieldViewSet):
    model = PidProviderConfig
    menu_label = _("Pid Provider Config")
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    list_per_page = 10

    # Configuração de listagem
    list_display = [
        "pid_provider_api_post_xml",
        "pid_provider_api_get_token",
    ]

    # Configuração de export
    list_export = [
        "pid_provider_api_post_xml",
        "pid_provider_api_get_token",
    ]
    export_filename = "pid_provider_config"


class FixPidV2ViewSet(CommonControlFieldViewSet):
    model = FixPidV2
    menu_label = _("Fix pid v2")
    menu_icon = "folder"
    add_to_settings_menu = False
    list_per_page = 10

    # Configuração de listagem
    list_display = [
        "pid_provider_xml",
        "correct_pid_v2",
        "fixed_in_core",
        "fixed_in_upload",
        "created",
        "updated",
    ]
    list_filter = {
        "fixed_in_core": ["exact"],
        "fixed_in_upload": ["exact"],
    }
    search_fields = (
        "correct_pid_v2",
        "pid_provider_xml__v3",
        "pid_provider_xml__pkg_name",
    )

    # Configuração de export
    list_export = [
        "pid_provider_xml",
        "correct_pid_v2",
        "fixed_in_core",
        "fixed_in_upload",
        "created",
        "updated",
    ]
    export_filename = "fix_pid_v2"


# Grupo de ViewSets
class PidProviderViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Pid Provider")
    menu_icon = "folder-open-inverse"
    menu_order = get_menu_order("pid_provider")
    items = (
        PidProviderConfigViewSet,
        PidProviderXMLViewSet,
        OtherPidViewSet,
        FixPidV2ViewSet,
    )


# Registrar o grupo de snippets
register_snippet(PidProviderViewSetGroup)
