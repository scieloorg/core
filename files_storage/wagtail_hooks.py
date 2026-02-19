from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import CreateView, SnippetViewSet

from config.menu import get_menu_order
from files_storage.models import MinioConfiguration


class MinioConfigurationCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


@register_snippet
class MinioConfigurationAdmin(SnippetViewSet):
    model = MinioConfiguration
    menu_label = _("Minio Configuration")
    add_view_class = MinioConfigurationCreateView
    menu_icon = "folder"
    menu_order = get_menu_order("files_storage")
    # no menu, ficará disponível como sub-menu em "Settings"
    add_to_settings_menu = True
    inspect_view_enabled = True

    list_per_page = 10
    list_display = (
        "name",
        "host",
        "bucket_root",
        "bucket_app_subdir",
    )
    search_fields = (
        "name",
        "host",
        "bucket_root",
        "bucket_app_subdir",
    )
