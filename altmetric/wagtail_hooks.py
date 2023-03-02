from django.utils.translation import gettext as _

from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    modeladmin_register,
    ModelAdminGroup,
)

from .models import RawAltmetric


class RawAltmetricAdmin(ModelAdmin):
    model = RawAltmetric
    menu_label = _("Altmetric")  # ditch this to use verbose_name_plural from model
    menu_icon = "folder-open-inverse"  # change as required
    # menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    list_display = (
        "issn_scielo",
        "extraction_date",
        "resource_type",
        "json",
    )

    search_fields = ("issn_scielo",)


modeladmin_register(RawAltmetricAdmin)
