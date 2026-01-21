from django.http import HttpResponseRedirect
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail_modeladmin.options import ModelAdmin, ModelAdminGroup, modeladmin_register
from wagtail_modeladmin.views import CreateView

from config.menu import get_menu_order

from .button_helpers import CountryHelper
from .models import (
    City,
    Country,
    CountryFile,
    CountryMatched,
    Location,
    State,
    StateMatched,
)
from .views import import_file_country, validate_country


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
    exclude_from_explorer = False
    list_display = ("name",)
    search_fields = ("name",)
    list_filter = ("status",)
    list_export = ("name",)
    export_filename = "cities"


class StateAdmin(ModelAdmin):
    model = State
    create_view_class = LocationCreateView
    menu_label = _("State")
    menu_icon = "folder"
    menu_order = 700
    add_to_settings_menu = False
    exclude_from_explorer = False
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
    list_filter = ("status",)
    export_filename = "states"


class CountryAdmin(ModelAdmin):
    model = Country
    create_view_class = LocationCreateView
    menu_label = _("Country")
    menu_icon = "folder"
    menu_order = 700
    add_to_settings_menu = False
    exclude_from_explorer = False
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
    list_filter = ("status",)
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


# modeladmin_register(LocationAdmin)
class LocationAdminGroup(ModelAdminGroup):
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

from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import (
    CreateView,
    SnippetViewSet,
    SnippetViewSetGroup,
)


@register_snippet
class CountryMatchedSnippetViewAdmin(SnippetViewSet):
    model = CountryMatched
    menu_label = "Correspondencia Country"
    menu_icon = "folder"
    search_fields = (
        "official__name",
    )
    list_display = ("official", "matched_list", "score")


@register_snippet
class StateMatchedSnippetViewAdmin(SnippetViewSet):
    model = StateMatched
    menu_label = "Correspondencia State"
    menu_icon = "folder"
    search_fields = (
        "official__name",
    )
    list_display = ("official", "matched_list", "score")
