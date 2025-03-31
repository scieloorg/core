from django.utils.translation import gettext as _
from wagtail import hooks
from wagtail_modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)

from wagtail_modeladmin.views import CreateView

from . import models
from config.menu import get_menu_order


class BaseOrganization:
    menu_icon = "folder"
    menu_order = get_menu_order("organizarion_publisher")
    add_to_settings_menu = False
    list_display = ("custom_name", "acronym")
    search_fields = ("name", "acronym")
    list_filter = "is_official"

    def custom_name(self, obj):
        return f"{str(self)}"

    custom_name.short_description = "name"
    custom_name.admin_order_field = "name"


class OrganizationPublisherAdmin(ModelAdmin, BaseOrganization):
    model = models.OrganizationPublisher
    menu_label = _("Organization Publisher")
    pass


class OrganizationOwnerAdmin(ModelAdmin, BaseOrganization):
    model = models.OrganizationOwner
    menu_label = _("Organization Owner")
    pass


class OrganizationSponsorAdmin(ModelAdmin, BaseOrganization):
    model = models.OrganizationSponsor
    menu_label = _("Organization Sponsor")
    pass


class OrganizationCopyrightAdmin(ModelAdmin, BaseOrganization):
    model = models.OrganizationCopyrightHolder
    menu_label = _("Organization copyright")
    pass


class OrganizationAdminGroup(ModelAdminGroup):
    menu_label = _("Organizations")
    menu_icon = "folder-open-inverse"
    menu_order = get_menu_order("organization")
    items = (
        OrganizationPublisherAdmin,
        OrganizationSponsorAdmin,
        OrganizationCopyrightAdmin,
        OrganizationOwnerAdmin,
    )


modeladmin_register(OrganizationAdminGroup)
