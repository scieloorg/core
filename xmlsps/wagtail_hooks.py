from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from wagtail.contrib.modeladmin.views import CreateView

from .models import XMLVersion


class XMLVersionCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class XMLVersionAdmin(ModelAdmin):
    list_per_page = 10
    model = XMLVersion
    inspect_view_enabled = True
    menu_label = _("XMLVersion")
    create_view_class = XMLVersionCreateView
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "pid_v3",
        "created",
        "updated",
    )
    # list_filter = ("is_published",)
    search_fields = ("pid_v3",)


modeladmin_register(XMLVersionAdmin)
