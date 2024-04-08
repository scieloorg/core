from django.utils.translation import gettext as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from config.menu import get_menu_order

from xml_validation.models import ValidationConfiguration


class ValidationConfigurationViewSet(SnippetViewSet):
    model = ValidationConfiguration
    icon = 'folder-open-inverse'
    add_to_admin_menu = True
    menu_label = _("Validation Configutarion")
    menu_order = get_menu_order("xml_validation")


register_snippet(ValidationConfigurationViewSet)

