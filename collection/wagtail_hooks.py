from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import CreateView, SnippetViewSet

from .models import Collection
from config.menu import get_menu_order


class CollectionCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


@register_snippet
class CollectionAdmin(SnippetViewSet):
    model = Collection
    add_view_class = CollectionCreateView
    inspect_view_enabled = True
    menu_label = _("Collection")
    menu_icon = "folder-open-inverse"
    menu_order = get_menu_order("collection")
    add_to_settings_menu = False
    list_display = (
        "main_name",
        "acron3",
        "platform_status",
        "status",
        "collection_type",
        "is_active",
        "updated",
    )
    list_filter = (
        "platform_status",
        "status",
        "collection_type",
        "is_active",
        "has_analytics",
    )
    search_fields = (
        "acron3",
        "acron2",
        "code",
        "domain",
        "main_name",
    )
    list_export = (
        "acron3",
        "acron2",
        "code",
        "domain",
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
