from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from .models import Event, JournalAndCollection


class EventCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class EventAdmin(ModelAdmin):
    model = Event
    create_view_class = EventCreateView
    menu_label = _("Event")
    menu_icon = "folder"
    menu_order = 400
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    def all_events(self, obj):
        return " | ".join([str(event) for event in obj.events_collection.all()])

    list_display = (
        "collection",
        "occurrence_date_year",
        "occurrence_date_month",
        "occurrence_date_day",
        "occurrence_type",
        "creator",
        "updated",
        "created",
        "updated_by",
    )
    search_fields = (
        "collection",
        "occurrence_date_year",
        "occurrence_date_month",
        "occurrence_date_day",
        "occurrence_type",
        "creator",
        "updated",
        "created",
        "updated_by",
    )
    list_export = (
        "collection",
        "occurrence_date_year",
        "occurrence_date_month",
        "occurrence_date_day",
        "occurrence_type",
        "creator",
        "updated",
        "created",
        "updated_by",
    )
    export_filename = "events"


class JournalAndCollectionCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class JournalAndCollectionAdmin(ModelAdmin):
    model = JournalAndCollection
    create_view_class = JournalAndCollectionCreateView
    menu_label = _("Journal and Collection")
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    def all_events(self, obj):
        return " | ".join([str(event) for event in obj.events_collection.all()])

    list_display = (
        "journal",
        "all_events",
        "creator",
        "updated",
        "created",
        "updated_by",
    )
    search_fields = ("journal", "creator", "updated", "created", "updated_by")
    list_export = (
        "journal",
        "all_events",
        "creator",
        "updated",
        "created",
        "updated_by",
    )
    export_filename = "journal_and_collection"


class JournalAndCollectionAdminGroup(ModelAdminGroup):
    menu_label = _("Indexing Journals in Collections")
    menu_icon = "folder-open-inverse"
    menu_order = 200
    items = (EventAdmin, JournalAndCollectionAdmin)


modeladmin_register(JournalAndCollectionAdminGroup)
