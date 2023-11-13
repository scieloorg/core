from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from wagtail.contrib.modeladmin.views import CreateView

from .models import Researcher


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
    search_fields = (
        "given_names",
        "last_name",
        "declared_name",
        "orcid",
    )


modeladmin_register(ResearcherAdmin)
