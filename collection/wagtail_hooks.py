from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from wagtail.contrib.modeladmin.views import CreateView

from .models import Collection


class CollectionCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class CollectionAdmin(ModelAdmin):
    model = Collection
    create_view_class = CollectionCreateView
    inspect_view_enabled = True
    menu_label = _("Collection")
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = ("main_name", "collection_type", "creator", "updated", "created", "updated_by")
    search_fields = ("main_name", "collection_type", "creator", "updated", "created", "updated_by")
    list_export = (
        "acron3",
        "acron2",
        "code",
        "domain",
        "name",
        "main_name",
        "status",
        "has_analytics",
        "collection_type",
        "is_active",
        "foundation_date",
        "creator",
        "updated",
        "created",
        "updated_by",
    )
    export_filename = "collections"


modeladmin_register(CollectionAdmin)
