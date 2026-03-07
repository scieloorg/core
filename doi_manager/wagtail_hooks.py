from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import CreateView, EditView

from config.menu import get_menu_order
from core.viewsets import CommonControlFieldViewSet

from .models import CrossRefConfiguration


class CrossRefConfigurationCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class CrossRefConfigurationEditView(EditView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class CrossRefConfigurationViewSet(CommonControlFieldViewSet):
    model = CrossRefConfiguration
    menu_label = _("CrossRef Configuration")
    menu_icon = "cog"
    menu_order = get_menu_order("doi_manager")
    add_to_settings_menu = False
    add_view_class = CrossRefConfigurationCreateView
    edit_view_class = CrossRefConfigurationEditView

    list_display = [
        "prefix",
        "depositor_name",
        "depositor_email_address",
        "registrant",
        "updated",
    ]
    search_fields = [
        "prefix",
        "depositor_name",
        "depositor_email_address",
        "registrant",
    ]
    list_export = [
        "prefix",
        "depositor_name",
        "depositor_email_address",
        "registrant",
        "updated",
    ]
    export_filename = "crossref_configurations"


register_snippet(CrossRefConfigurationViewSet)


@hooks.register("register_permissions")
def register_crossref_configuration_permissions():
    content_type = ContentType.objects.get_for_model(
        CrossRefConfiguration, for_concrete_model=False
    )
    return Permission.objects.filter(content_type=content_type)
