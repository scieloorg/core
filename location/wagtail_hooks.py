from django.http import HttpResponseRedirect
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import CreateView, SnippetViewSet, SnippetViewSetGroup

from .button_helpers import CountryHelper
from .models import City, Country, CountryFile, Location, State
from .views import import_file_country, validate_country
from config.menu import get_menu_order


class LocationCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class LocationAdmin(SnippetViewSet):
    model = Location
    add_view_class = LocationCreateView
    menu_label = _("Location")
    menu_icon = "folder"
    menu_order = 700
    add_to_settings_menu = False
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


class CityAdmin(SnippetViewSet):
    model = City
    add_view_class = LocationCreateView
    menu_label = _("City")
    menu_icon = "folder"
    menu_order = 700
    add_to_settings_menu = False
    list_display = ("name",)
    search_fields = ("name",)
    list_export = ("name",)
    export_filename = "cities"


class StateAdmin(SnippetViewSet):
    model = State
    add_view_class = LocationCreateView
    menu_label = _("State")
    menu_icon = "folder"
    menu_order = 700
    add_to_settings_menu = False
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
    export_filename = "states"


class CountryAdmin(SnippetViewSet):
    model = Country
    add_view_class = LocationCreateView
    menu_label = _("Country")
    menu_icon = "folder"
    menu_order = 700
    add_to_settings_menu = False
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


class CountryFileAdmin(SnippetViewSet):
    model = CountryFile
    button_helper_class = CountryHelper
    menu_label = "Country Upload"
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    list_display = ("attachment", "line_count", "is_valid")
    list_filter = ("is_valid",)
    search_fields = ("attachment",)


class LocationAdminGroup(SnippetViewSetGroup):
    menu_label = _("Location")
    menu_icon = "folder-open-inverse"
    menu_order = get_menu_order("location")
    items = (
        LocationAdmin,
        CityAdmin,
        StateAdmin,
        CountryAdmin,
        CountryFileAdmin,
    )


register_snippet(LocationAdminGroup)


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
