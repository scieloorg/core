from django.http import HttpResponseRedirect
from django.urls import include, path
from django.utils.translation import gettext as _
from wagtail import hooks
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from .button_helpers import ScimagoHelper
from .models import Institution, Scimago, ScimagoFile, Sponsor
from .views import import_file_scimago, validate_scimago


class InstitutionIdentificationCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class InstitutionIdentificationAdmin(ModelAdmin):
    model = InstitutionIdentification
    create_view_class = InstitutionIdentificationCreateView
    menu_label = _("InstitutionIdentification")
    menu_icon = "folder"
    menu_order = 800
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = (
        "name",
        "acronym",
        "is_official",
        "updated",
        "created",
    )
    list_filter = ("is_official",)
    search_fields = (
        "name",
        "acronym",
    )
    list_export = (
        "name",
        "acronym",
        "is_official",
        "updated",
        "created",
        "creator",
        "updated_by",
    )
    export_filename = "institution_institution_identification"


class InstitutionCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class InstitutionAdmin(ModelAdmin):
    model = Institution
    create_view_class = InstitutionCreateView
    menu_label = _("Institution")
    menu_icon = "folder"
    menu_order = 800
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = (
        "name",
        "institution_type",
        "creator",
        "updated",
        "created",
        "updated_by",
    )
    search_fields = (
        "name",
        "institution_type",
        "creator__username",
        "updated",
        "created",
        "updated_by__username",
    )
    list_export = (
        "name",
        "institution_type",
        "level_1",
        "level_2",
        "level_3",
        "creator",
        "updated",
        "created",
        "updated_by",
    )
    export_filename = "institutions"


class SponsorCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class SponsorAdmin(ModelAdmin):
    model = Sponsor
    create_view_class = SponsorCreateView
    menu_label = _("Sponsor")
    menu_icon = "folder"
    menu_order = 900
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = ("institution",)
    search_fields = (
        "institution__name",
        "institution__acronym",
        "institution__level_1",
        "institution__level_2",
        "institution__level_3",
        # # "location",
        # "institution__official",
        "institution__is_official",
    )
    list_export = (
        "institution",
        "institution__name",
        "institution__acronym",
        "institution__level_1",
        "institution__level_2",
        "institution__level_3",
        "location",
        "official",
        "institution__is_official",
    )
    export_filename = "sponsor"


class ScimgoCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ScimagoAdmin(ModelAdmin):
    model = Scimago
    create_view_class = ScimgoCreateView
    menu_label = _("Scimago")
    menu_icon = "folder"
    menu_order = 700
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "institution",
        "country",
        "url",
    )
    search_fields = (
        "institution",
        "country",
        "url",
    )
    list_export = (
        "institution",
        "country",
        "url",
    )
    export_filename = "scimago"


class ScimagoFileAdmin(ModelAdmin):
    model = ScimagoFile
    button_helper_class = ScimagoHelper
    menu_label = "Scimago Upload"
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ("attachment", "line_count", "is_valid")
    list_filter = ("is_valid",)
    search_fields = ("attachment",)


class InstitutionsAdminGroup(ModelAdminGroup):
    menu_label = _("Institutions")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = 7
    items = (
        InstitutionIdentificationAdmin,
        InstitutionAdmin,
        SponsorAdmin,
        ScimagoAdmin,
        ScimagoFileAdmin,
    )


modeladmin_register(InstitutionsAdminGroup)


@hooks.register("register_admin_urls")
def register_url():
    return [
        path(
            "institution/scimago/validate",
            validate_scimago,
            name="validate_scimago",
        ),
        path(
            "institution/scimago/import_file",
            import_file_scimago,
            name="import_file_scimago",
        ),
    ]
