from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail_modeladmin.options import ModelAdmin, ModelAdminGroup, modeladmin_register
from wagtail_modeladmin.views import CreateView

from config.menu import get_menu_order

from .models import (
    Affiliation,
    NewResearcher,
    PersonName,
    Researcher,
    ResearcherIdentifier,
    ResearcherOrcid,
)


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
        "affiliation",
        "created",
        "updated",
    )
    search_fields = (
        "person_name__fullname",
        "person_name__declared_name",
        "affiliation__institution__institution_identification__name",
        "affiliation__institution__institution_identification__acronym",
    )


class ResearcherIdentifierCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ResearcherIdentifierAdmin(ModelAdmin):
    model = ResearcherIdentifier
    create_view_class = ResearcherIdentifierCreateView
    menu_label = _("Researcher Identifier")
    menu_icon = "folder"
    menu_order = 9
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "identifier",
        "source_name",
        "created",
        "updated",
    )
    list_filter = ("source_name",)
    search_fields = ("identifier",)


class AffiliationAdmin(ModelAdmin):
    model = Affiliation
    menu_label = _("Affiliation")
    menu_icon = "folder"
    menu_order = 9
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        # "institution",
        "created",
        "updated",
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
        "fullname",
        "gender",
        "created",
        "updated",
    )
    list_filter = ("suffix", "gender", "gender_identification_status")
    search_fields = ("fullname", "declared_name")


class ResearcherAdminGroup(ModelAdminGroup):
    menu_label = _("Researchers")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = get_menu_order("researcher")
    items = (
        ResearcherIdentifierAdmin,
        ResearcherAdmin,
        PersonNameAdmin,
        AffiliationAdmin,
    )


class ResearcherOrganizationAdminViewSet(SnippetViewSet):
    model = ResearcherOrcid
    menu_icon = "folder"
    menu_label = _("New Researcher")
    menu_order = get_menu_order("new_researcher")
    list_display = ["__str__", "get_fullname_researcher"]
    inspect_view_enabled = True
    add_to_admin_menu = True

register_snippet(ResearcherOrganizationAdminViewSet)

