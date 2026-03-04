from django.utils.translation import gettext_lazy as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from config.menu import get_menu_order
from .models import RawAltmetric


@register_snippet
class RawAltmetricAdmin(SnippetViewSet):
    model = RawAltmetric
    menu_label = _("Altmetric")  # ditch this to use verbose_name_plural from model
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = get_menu_order("altmetric")  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu

    list_display = (
        "issn_scielo",
        "extraction_date",
        "resource_type",
        "json",
    )

    search_fields = ("issn_scielo",)
