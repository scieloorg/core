from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from config.menu import get_menu_order

from .models import UnexpectedEvent, Hello


class UnexpectedEventModelAdmin(ModelAdmin):
    model = UnexpectedEvent
    inspect_view_enabled = True
    menu_label = _("Unexpected Events")
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "exception_type",
        "exception_msg",
        "traceback",
        "created",
    )
    list_filter = ("exception_type",)
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


class HelloModelAdmin(ModelAdmin):
    model = Hello
    inspect_view_enabled = True
    menu_label = _("Hello events")
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False

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


class UnexpectedEventModelAdminGroup(ModelAdminGroup):
    menu_icon = "folder"
    menu_label = _("Unexpected errors")
    # menu_order = get_menu_order("journal")
    menu_order = 200
    items = (UnexpectedEventModelAdmin, HelloModelAdmin)
    menu_order = get_menu_order("unexpected-error")


modeladmin_register(UnexpectedEventModelAdminGroup)
