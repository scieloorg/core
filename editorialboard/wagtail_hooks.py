from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup
from wagtail_modeladmin.views import CreateView

from config.menu import get_menu_order

from .models import EditorialBoardMember, RoleModel


class EditorialBoardMemberCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class EditorialBoardMemberAdmin(SnippetViewSet):
    model = EditorialBoardMember
    menu_label = _("Editorial Board Member")
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "journal",
        "researcher",
    )
    search_fields = (
        "journal__title",
        "researcher__fullname",
    )


class RoleModelAdmin(SnippetViewSet):
    model = RoleModel
    menu_label = _("RoleModel")
    menu_icon = "folder"
    menu_order = 9
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ("declared_role", "std_role", "updated", "created")
    list_filter = ("std_role",)
    search_fields = ("declared_role",)


class EditorialBoardMemberGroupViewSet(SnippetViewSetGroup):
    menu_label = "Editorial Board Member"
    menu_icon = "folder-open-inverse"
    menu_order = get_menu_order("editorialboard")  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_admin_menu = True
    items = (
        EditorialBoardMemberAdmin,
        RoleModelAdmin,
    )
register_snippet(EditorialBoardMemberGroupViewSet)
