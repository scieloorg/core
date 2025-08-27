from django.http import HttpResponseRedirect
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail_modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail_modeladmin.views import CreateView, EditView

from config.menu import get_menu_order
from .button_helpers import GenericThematicAreaHelper, ThematicAreaHelper
from .models import (
    GenericThematicArea,
    GenericThematicAreaFile,
    ThematicArea,
    ThematicAreaFile,
)


class GenericThematicAreaEditView(EditView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class GenericThematicAreaCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class GenericThematicAreaFileCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class GenericThematicAreaAdmin(ModelAdmin):
    model = GenericThematicArea
    create_view_class = GenericThematicAreaCreateView
    menu_label = _("Generic Thematic Area")
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = (
        "text",
        "language",
        "origin",
        "level",
        "level_up",
        "creator",
        "updated",
        "created",
    )
    search_fields = (
        "text",
        "origin",
        "level",
    )
    list_export = (
        "text",
        "lang",
        "origin",
        "level",
        "creator",
        "updated",
        "created",
    )
    export_filename = "generic_thematic_areas"


class GenericThematicAreaFileAdmin(ModelAdmin):
    model = GenericThematicAreaFile
    ordering = ("-updated",)
    create_view_class = GenericThematicAreaFileCreateView
    button_helper_class = GenericThematicAreaHelper
    menu_label = _("Generic Thematic Areas Upload")
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "attachment",
        "line_count",
        "is_valid",
        "creator",
        "updated",
        "created",
    )
    list_filter = ("is_valid",)
    search_fields = ("attachment__title",)


class GenericThematicAreaAdminGroup(ModelAdminGroup):
    menu_label = _("Generic Thematic Areas")
    menu_icon = "folder-open-inverse"
    menu_order = 600
    items = (
        GenericThematicAreaAdmin,
        GenericThematicAreaFileAdmin,
    )


# modeladmin_register(GenericThematicAreaAdminGroup)


@hooks.register("register_admin_urls")
def register_url():
    return [
        path(
            "generic_thematic_areas/genericthematicareafile/",
            include("thematic_areas.urls", namespace="generic_thematic_areas"),
        ),
    ]


class ThematicAreaEditView(EditView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ThematicAreaCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ThematicAreaFileCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ThematicAreaAdmin(ModelAdmin):
    model = ThematicArea
    create_view_class = ThematicAreaCreateView
    menu_label = _("Thematic Area")
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = (
        "level0",
        "level1",
        "level2",
        "creator",
        "updated",
        "created",
    )
    search_fields = (
        "level0",
        "level1",
        "level2",
    )
    list_export = (
        "level0",
        "level1",
        "level2",
        "creator",
        "updated",
        "created",
    )
    export_filename = "thematic_areas"


class ThematicAreaFileAdmin(ModelAdmin):
    model = ThematicAreaFile
    ordering = ("-updated",)
    create_view_class = ThematicAreaFileCreateView
    button_helper_class = ThematicAreaHelper
    menu_label = _("Thematic Areas Upload")
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "attachment",
        "line_count",
        "is_valid",
        "creator",
        "updated",
        "created",
    )
    list_filter = ("is_valid",)
    search_fields = ("attachment__title",)


class ThematicAreaAdminGroup(ModelAdminGroup):
    menu_label = _("Thematic Areas")
    menu_icon = "folder-open-inverse"
    menu_order = get_menu_order("thematic_areas")
    items = (
        ThematicAreaAdmin,
        ThematicAreaFileAdmin,
    )


# modeladmin_register(ThematicAreaAdminGroup)


@hooks.register("register_admin_urls")
def register_url():
    return [
        path(
            "thematic_areas/thematicareafile/",
            include("thematic_areas.urls", namespace="thematic_areas"),
        ),
    ]
