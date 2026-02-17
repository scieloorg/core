from django.utils.translation import gettext_lazy as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from . import models
from config.menu import get_menu_order


class OrganizationViewSet(SnippetViewSet):
    model = models.Organization
    menu_icon = "folder"
    menu_label = _("Organization")
    menu_order = get_menu_order("organization")
    list_display = ["__str__", "acronym"]
    search_fields = ["name", "acronym"]
    list_filter = ["is_official"]
    inspect_view_enabled = True
    add_to_admin_menu = True


class OrganizationDivisionViewSet(SnippetViewSet):
    model = models.OrganizationDivision
    menu_icon = "list-ul"
    menu_label = _("Organization Division")
    menu_order = get_menu_order("organization") + 1
    list_display = ["__str__", "organization", "level_1", "level_2", "level_3"]
    search_fields = ["level_1", "level_2", "level_3"]
    list_filter = ["organization"]
    inspect_view_enabled = True
    add_to_admin_menu = True


register_snippet(OrganizationViewSet)
register_snippet(OrganizationDivisionViewSet)
