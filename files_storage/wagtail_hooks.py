from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from wagtail.contrib.modeladmin.views import CreateView

from config.menu import get_menu_order
from files_storage.models import MinioConfiguration


class MinioConfigurationCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class MinioConfigurationAdmin(ModelAdmin):
    model = MinioConfiguration
    menu_label = _("Minio Configuration")
    create_view_class = MinioConfigurationCreateView
    menu_icon = "folder"
    menu_order = get_menu_order("files_storage")
    # no menu, ficará disponível como sub-menu em "Settings"
    add_to_settings_menu = True
    exclude_from_explorer = False
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


modeladmin_register(MinioConfigurationAdmin)
