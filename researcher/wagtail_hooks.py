from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import CreateView as CreateViewAdmin
from wagtail.snippets.views.snippets import EditView, SnippetViewSet
from wagtail_modeladmin.options import ModelAdmin, ModelAdminGroup
from wagtail_modeladmin.views import CreateView

from config.menu import get_menu_order

from .models import (
    Affiliation,
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


class ResearcherOrcidFormValidationMixin:
    def form_valid(self, form):
        form_kwargs = self.get_form_kwargs()
        forms_data = form_kwargs['data']
        total_forms = int(forms_data.get('researcher_orcid-TOTAL_FORMS', 0))
        if total_forms == 0:
            form.add_error(None, "You must add at least one researcher to the ORCID.")
            return self.form_invalid(form)
        
        last_index = total_forms - 1
        prefix = f"researcher_orcid-{last_index}"
        marked_for_deletion = forms_data.get(f'{prefix}-DELETE') == '1'
        given_names = forms_data.get(f'{prefix}-given_names', '').strip()
        last_name = forms_data.get(f'{prefix}-last_name', '').strip()
        affiliation = forms_data.get(f'{prefix}-affiliation', 'null')
        
        if marked_for_deletion or not given_names or not last_name or affiliation == 'null':
            form.add_error(None, "You must add at least one valid researcher to the ORCID.")
            return self.form_invalid(form)
        return super().form_valid(form)


class ResearcherOrcidCreateView(ResearcherOrcidFormValidationMixin, CreateViewAdmin):
    ...


class ResearcherOrcidEditView(ResearcherOrcidFormValidationMixin, EditView):
    ...


class ResearcherOrganizationAdminViewSet(SnippetViewSet):
    model = ResearcherOrcid
    add_view_class = ResearcherOrcidCreateView
    edit_view_class = ResearcherOrcidEditView
    menu_icon = "folder"
    menu_label = _("New Researcher")
    menu_order = get_menu_order("new_researcher")
    list_display = ["__str__", "get_fullname_researcher"]
    inspect_view_enabled = True
    add_to_admin_menu = True

register_snippet(ResearcherOrganizationAdminViewSet)

