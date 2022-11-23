from django.urls import include, path
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _

from wagtail.core import hooks
from wagtail.contrib.modeladmin.views import CreateView, EditView
from wagtail.contrib.modeladmin.options import (ModelAdmin, modeladmin_register, ModelAdminGroup)

from .models import ThematicArea, ThematicAreaFile, GenericThematicArea, GenericThematicAreaFile
from .button_helpers import ThematicAreaHelper, GenericThematicAreaHelper


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
    menu_label = _('Generic Thematic Area')
    menu_icon = 'folder'
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('text', 'lang', 'origin', 'level', 'level_up', 'creator',
                    'updated', 'created',)
    search_fields = ('text',)
    list_export = ('text', 'lang', 'origin', 'level', 'creator',
                   'updated', 'created',)
    export_filename = 'generic_thematic_areas'


class GenericThematicAreaFileAdmin(ModelAdmin):
    model = GenericThematicAreaFile
    ordering = ('-updated',)
    create_view_class = GenericThematicAreaFileCreateView
    button_helper_class = GenericThematicAreaHelper
    menu_label = _('Generic Thematic Areas Upload')
    menu_icon = 'folder'
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ('attachment', 'line_count', 'is_valid', 'creator',
                    'updated', 'created',)
    list_filter = ('is_valid',)
    search_fields = ('attachment',)


class GenericThematicAreaAdminGroup(ModelAdminGroup):
    menu_label = _('Generic Thematic Areas')
    menu_icon = 'folder-open-inverse'
    menu_order = 200
    items = (GenericThematicAreaAdmin, GenericThematicAreaFileAdmin,)


modeladmin_register(GenericThematicAreaAdminGroup)


@hooks.register('register_admin_urls')
def register_url():
    return [
        path('generic_thematic_areas/genericthematicareafile/',
             include('thematic_areas.urls', namespace='generic_thematic_areas'), ),
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
    menu_label = _('Thematic Area')
    menu_icon = 'folder'
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('level0', 'level1', 'level2', 'creator',
                    'updated', 'created',)
    search_fields = ('level0', 'level1', 'level2',)
    list_export = ('level0', 'level1', 'level2', 'creator',
                   'updated', 'created',)
    export_filename = 'thematic_areas'


class ThematicAreaFileAdmin(ModelAdmin):
    model = ThematicAreaFile
    ordering = ('-updated',)
    create_view_class = ThematicAreaFileCreateView
    button_helper_class = ThematicAreaHelper
    menu_label = _('Thematic Areas Upload')
    menu_icon = 'folder'
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ('attachment', 'line_count', 'is_valid', 'creator',
                    'updated', 'created',)
    list_filter = ('is_valid',)
    search_fields = ('attachment',)


class ThematicAreaAdminGroup(ModelAdminGroup):
    menu_label = _('Thematic Areas')
    menu_icon = 'folder-open-inverse'
    menu_order = 200
    items = (ThematicAreaAdmin, ThematicAreaFileAdmin,)


modeladmin_register(ThematicAreaAdminGroup)


@hooks.register('register_admin_urls')
def register_url():
    return [
        path('thematic_areas/thematicareafile/',
             include('thematic_areas.urls', namespace='thematic_areas'), ),
    ]
