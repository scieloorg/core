from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import ModelAdmin, ModelAdminGroup, modeladmin_register
from wagtail.contrib.modeladmin.views import CreateView

from .models import Researcher, OrcidModel, PersonName


class ResearcherCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ResearcherAdmin(ModelAdmin):
    model = Researcher
    create_view_class = ResearcherCreateView
    menu_label = _("Researcher")
    menu_icon = "folder"
    menu_order = 9
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "person_name",
        "orcid",
        "lattes",
        "created",
        "updated",
    )
    list_filter = ("gender", "gender_identification_status")
    search_fields = (
        "orcid__person_names__given_names",
        "orcid__person_names__last_name",
        "orcid__person_names__suffix",
        "orcid__person_names__declared_name",
        "person_name__given_names",
        "person_name__last_name",
        "person_name__suffix",
        "person_name__declared_name",
        "orcid__orcid",
        "lattes",
    )


class OrcidModelCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class OrcidModelAdmin(ModelAdmin):
    model = OrcidModel
    create_view_class = OrcidModelCreateView
    menu_label = _("OrcidModel")
    menu_icon = "folder"
    menu_order = 9
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "orcid",
        "person_names",
        "created",
        "updated",
    )
    search_fields = (
        "person_names__given_names",
        "person_names__last_name",
        "person_names__suffix",
        "person_names__declared_name",
        "orcid",
    )


class PersonNameCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class PersonNameAdmin(ModelAdmin):
    model = PersonName
    create_view_class = PersonNameCreateView
    menu_label = _("PersonName")
    menu_icon = "folder"
    menu_order = 9
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "declared_name",
        "created",
        "updated",
    )
    search_fields = (
        "given_names",
        "last_name",
        "suffix",
        "declared_name",
    )


class ResearcherAdminGroup(ModelAdminGroup):
    menu_label = _("Researchers")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = 7
    items = (ResearcherAdmin, OrcidModelAdmin, PersonNameAdmin)


modeladmin_register(ResearcherAdminGroup)
