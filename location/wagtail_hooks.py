from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from django.urls import include, path
from wagtail.contrib.modeladmin.options import ModelAdmin, ModelAdminGroup, modeladmin_register
from wagtail.contrib.modeladmin.views import CreateView
from wagtail import hooks

from .models import City, Region, State, Country, Location, CountryFile, Address
from .views import import_file_country, validate_country
from .button_helpers import CountryHelper


class LocationCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class LocationAdmin(ModelAdmin):
    model = Location
    create_view_class = LocationCreateView
    menu_label = _("Location")
    menu_icon = "folder"
    menu_order = 700
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = (
        "country",
        "state",
        "city",
        "creator",
        "updated",
        "created",
    )
    search_fields = (
        "country__name",
        "state__name",
        "city__name",
    )
    list_export = (
        "country",
        "state",
        "city",
    )
    export_filename = "locations"


class CityAdmin(ModelAdmin):
    model = City
    create_view_class = LocationCreateView
    menu_label = _("City")
    menu_icon = "folder"
    menu_order = 700
    add_to_settings_menu = False
    exclude_from_explorer = (
        False
    )
    list_display = (
        "name",
    )
    search_fields = (
        "name",
    )
    list_export = (
        "name",
    )
    export_filename = "cities"


class RegionAdmin(ModelAdmin):
    model = Region
    create_view_class = LocationCreateView
    menu_label = _("Region")
    menu_icon = "folder"
    menu_order = 700
    add_to_settings_menu = False
    exclude_from_explorer = (
        False
    )
    list_display = (
        "name",
        "acronym",
    )
    search_fields = (
        "name",
        "acronym",
    )
    list_export = (
        "name",
        "acronym",
    )
    export_filename = "regions"


class StateAdmin(ModelAdmin):
    model = State
    create_view_class = LocationCreateView
    menu_label = _("State")
    menu_icon = "folder"
    menu_order = 700
    add_to_settings_menu = False
    exclude_from_explorer = (
        False
    )
    list_display = (
        "name",
        "acronym",
        "region",
    )
    search_fields = (
        "name",
        "acronym",
        "region",
    )
    list_export = (
        "name",
        "acronym",
        "region",
    )
    export_filename = "regions"

class AddressAdmin(ModelAdmin):
    model = Address
    create_view_class = LocationCreateView
    menu_label = _("Address")
    menu_icon = "folder"
    menu_order = 800
    add_to_settings_menu = False
    exclude_from_explorer = (
        False
    )
    list_display = (
        "name",
    )
    search_fields = (
        "name",
    )
    list_export = (
        "name",
    )


class CountryAdmin(ModelAdmin):
    model = Country
    create_view_class = LocationCreateView
    menu_label = _("Country")
    menu_icon = "folder"
    menu_order = 700
    add_to_settings_menu = False
    exclude_from_explorer = (
        False
    )
    list_display = (
        "name",
        "acronym",
        "acron3",
    )
    search_fields = (
        "name",
        "acronym",
        "acron3",
    )
    list_export = (
        "name",
        "acronym",
        "acron3",
    )
    export_filename = "countries"


class CountryFileAdmin(ModelAdmin):
    model = CountryFile
    button_helper_class = CountryHelper
    menu_label = "Country Upload"
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ("attachment", "line_count", "is_valid")
    list_filter = ("is_valid",)
    search_fields = ("attachment",)


#modeladmin_register(LocationAdmin)
class LocationAdminGroup(ModelAdminGroup):
    menu_label = _("Location")
    menu_icon = "folder-open-inverse"
    menu_order = 8
    items = (
        LocationAdmin,
        CityAdmin,
        RegionAdmin,
        StateAdmin,
        CountryAdmin,
        CountryFileAdmin,
        AddressAdmin,
    )


modeladmin_register(LocationAdminGroup)


@hooks.register("register_admin_urls")
def register_url():
    return [
        path(
            "location/country/validate",
            validate_country,
            name="validate_country",
        ),
        path(
            "location/country/import_file",
            import_file_country,
            name="import_file_country",
        ),
    ]