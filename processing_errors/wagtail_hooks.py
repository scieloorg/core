from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from wagtail.contrib.modeladmin.views import CreateView

from .models import ProcessingError


class ProcessingErrorCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ProcessingErrorAdmin(ModelAdmin):
    model = ProcessingError
    inspect_view_enabled = True
    menu_label = _("Processing Error")
    create_view_class = ProcessingErrorCreateView
    menu_icon = "folder"
    menu_order = 900
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "item",
        "description",
        "type",
        "step",
    )


# modeladmin_register(ProcessingErrorAdmin)
