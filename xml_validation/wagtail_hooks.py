from django.utils.translation import gettext_lazy as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup
from config.menu import get_menu_order

from xml_validation.models import ValidationConfiguration, VersionSPS


class ValidationConfigurationViewSet(SnippetViewSet):
    model = ValidationConfiguration
    icon = 'folder-open-inverse'
    menu_label = _("Validation Configutarion")
    menu_order = 1


class VersionSPSViewSet(SnippetViewSet):
    model = VersionSPS
    icon = 'folder-open-inverse'
    menu_label = _("SciELO Publishing Schema")
    menu_order = 2


class XmlValidationGroup(SnippetViewSetGroup):
    items = (ValidationConfigurationViewSet, VersionSPSViewSet)
    menu_order = get_menu_order("xml_validation")


register_snippet(XmlValidationGroup)