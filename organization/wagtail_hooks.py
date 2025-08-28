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


register_snippet(OrganizationViewSet)
