from django.urls import include, path
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _

from wagtail.core import hooks
from wagtail.contrib.modeladmin.views import CreateView, EditView
from wagtail.contrib.modeladmin.options import (ModelAdmin, modeladmin_register, ModelAdminGroup)

from .models import ThematicArea, ThematicAreaFile
from .button_helpers import ThematicAreaHelper


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
                    'updated', 'created', )
    search_fields = ('level0', 'level1', 'level2', )
    list_export = ('level0', 'level1', 'level2', 'creator',
                   'updated', 'created', )
    export_filename = 'thematic_areas'


class ThematicAreaFileAdmin(ModelAdmin):
    model = ThematicAreaFile
    ordering = ('-updated',)
    create_view_class=ThematicAreaFileCreateView
    button_helper_class = ThematicAreaHelper
    menu_label = _('Thematic Areas Upload')
    menu_icon = 'folder'
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ('attachment', 'line_count', 'is_valid', 'creator',
                    'updated', 'created', )
    list_filter = ('is_valid', )
    search_fields = ('attachment', )


class ThematicAreaAdminGroup(ModelAdminGroup):
    menu_label = _('Thematic Areas')
    menu_icon = 'folder-open-inverse'
    menu_order = 200
    items = (ThematicAreaAdmin, ThematicAreaFileAdmin,)


modeladmin_register(ThematicAreaAdminGroup)


@hooks.register('register_admin_urls')
def register_url():
    return [
        path('thematic_areas/ThematicAreafile/',
        include('thematic_areas.urls', namespace='thematic_areas')),
    ]
