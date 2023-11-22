from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    modeladmin_register,
)
from django.utils.translation import gettext as _

from .models import ReportCSV


class ReportCSVAdmin(ModelAdmin):
    model = ReportCSV
    menu_label = _("Report CSV")
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "title",
        "publication_year",
        "created",
        "updated",
    )
    list_filter = (
        "publication_year",
        "title",
    )
    
    search_fields = (
        "title", 
    )



modeladmin_register(ReportCSVAdmin)