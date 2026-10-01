import django_filters
from django import forms
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from wagtail.admin.filters import WagtailFilterSet
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import CreateView, SnippetViewSet

from . import choices
from .models import Collection
from config.menu import get_menu_order


class CollectionCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class CollectionFilterSet(WagtailFilterSet):
    # django-filter não gera filtro automaticamente para ArrayField
    network_classification = django_filters.MultipleChoiceFilter(
        label=_("Network classification"),
        choices=choices.NETWORK_CLASSIFICATION,
        widget=forms.CheckboxSelectMultiple,
        method="filter_network_classification",
    )

    class Meta:
        model = Collection
        fields = [
            "platform_status",
            "network_classification",
            "status",
            "collection_type",
            "is_active",
            "has_analytics",
        ]

    def filter_network_classification(self, queryset, name, value):
        if not value:
            return queryset
        # coleções que tenham ao menos uma das classificações selecionadas
        return queryset.filter(**{f"{name}__overlap": value})


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
        "network_classification",
        "status",
        "collection_type",
        "is_active",
        "updated",
    )
    filterset_class = CollectionFilterSet
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
        "platform_status",
        "network_classification",
        "status",
        "has_analytics",
        "collection_type",
        "is_active",
        "foundation_date",
        "network_classification",
        "creator",
        "updated",
        "created",
        "updated_by",
    )
    export_filename = "collections"
