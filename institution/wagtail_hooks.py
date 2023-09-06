from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from .models import Institution, Sponsor


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
    list_display = (
        "name",
        "acronym",
        "level_1",
        "level_2",
        "level_3",
        "location",
        "official",
        "is_official",
    )
    search_fields = (
        "name",
        "acronym",
        "level_1",
        "level_2",
        "level_3",
        "location",
        "official",
        "is_official",
    )
    list_export = (
        "name",
        "acronym",
        "level_1",
        "level_2",
        "level_3",
        "location",
        "official",
        "is_official",
    )
    export_filename = "sponsor"


class InstitutionsAdminGroup(ModelAdminGroup):
    menu_label = _("Institutions")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (InstitutionAdmin, SponsorAdmin)


modeladmin_register(InstitutionsAdminGroup)
