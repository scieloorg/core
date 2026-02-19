from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from config.menu import get_menu_order

from .models import UnexpectedEvent, Hello


class UnexpectedEventModelAdmin(SnippetViewSet):
    model = UnexpectedEvent
    inspect_view_enabled = True
    menu_label = _("Unexpected Events")
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    list_per_page = 10

    list_display = (
        "item",
        "action",
        "exception_type",
        "exception_msg",
        "created",
    )
    list_filter = ("action", "exception_type", )
    search_fields = (
        "exception_msg",
        "detail",
        "action",
        "item",
    )
    inspect_view_fields = (
        "action",
        "item",
        "exception_type",
        "exception_msg",
        "traceback",
        "detail",
        "created",
    )


class HelloModelAdmin(SnippetViewSet):
    model = Hello
    inspect_view_enabled = True
    menu_label = _("Hello events")
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    list_per_page = 10

    list_display = (
        "status",
        "exception_type",
        "exception_msg",
        "traceback",
        "created",
    )
    list_filter = ("status", "exception_type",)
    search_fields = (
        "exception_msg",
        "detail",
    )
    inspect_view_fields = (
        "exception_type",
        "exception_msg",
        "traceback",
        "detail",
        "created",
    )


class UnexpectedEventModelAdminGroup(SnippetViewSetGroup):
    menu_icon = "folder"
    menu_label = _("Unexpected errors")
    menu_order = get_menu_order("tracker")
    items = (UnexpectedEventModelAdmin, HelloModelAdmin)


register_snippet(UnexpectedEventModelAdminGroup)
