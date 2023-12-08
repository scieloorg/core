from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.translation import gettext as _
from wagtail import hooks
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from .button_helper import EditorialBoardMemberHelper
from .models import EditorialBoardMember, EditorialBoardMemberFile
from .views import import_file_ebm, validate_ebm


class EditorialBoardMemberAdmin(ModelAdmin):
    model = EditorialBoardMember
    menu_label = _("Editorial Board Member")
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False


class EditorialBoardMemberFileAdmin(ModelAdmin):
    model = EditorialBoardMemberFile
    button_helper_class = EditorialBoardMemberHelper
    menu_label = "Editorial Board Member Upload"
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ("attachment", "line_count", "is_valid")
    list_filter = ("is_valid",)
    search_fields = ("attachment",)


modeladmin_register(ResearcherAdmin)


class EditorialBoardMemberAdminGroup(ModelAdminGroup):
    menu_label = "Editorial Board Member"
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (
        EditorialBoardMemberAdmin,
        EditorialBoardMemberFileAdmin,
    )


# modeladmin_register(EditorialBoardMemberAdminGroup)


@hooks.register("register_admin_urls")
def register_editorial_url():
    return [
        path(
            "editorialboard/editorialboradmember/validate",
            validate_ebm,
            name="validate_ebm",
        ),
        path(
            "editorialboard/editorialboradmember/import_file",
            import_file_ebm,
            name="import_file_ebm",
        ),
    ]
