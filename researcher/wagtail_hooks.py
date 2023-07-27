from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView
from wagtail.core import hooks

from .button_helper import EditorialBoardMemberHelper
from .models import EditorialBoardMember, EditorialBoardMemberFile, Researcher
from .views import import_file_ebm, validate_ebm


class ResearcherCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ResearcherAdmin(ModelAdmin):
    model = Researcher
    create_view_class = ResearcherCreateView
    menu_label = _("Researcher")
    menu_icon = "folder"
    menu_order = 1000
    add_to_settings_menu = False
    exclude_from_explorer = False
    search_fields = ("given_names", "last_name")


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


modeladmin_register(EditorialBoardMemberAdminGroup)


@hooks.register("register_admin_urls")
def register_editorial_url():
    return [
        path(
            "researcher/editorialboradmember/validate",
            validate_ebm,
            name="validate_ebm",
        ),
        path(
            "researcher/editorialboradmember/import_file",
            import_file_ebm,
            name="import_file_ebm",
        ),
    ]
