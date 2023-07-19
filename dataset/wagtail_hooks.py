from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from dataset.models import Dataset, Dataverse, File


class DataSetCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class DataSetAdmin(ModelAdmin):
    model = Dataset
    create_view_class = DataSetCreateView
    menu_label = _("Data set")
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False
    exclude_from_explorer = False


class DataVerseCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class DataVerseAdmin(ModelAdmin):
    model = Dataverse
    create_view_class = DataVerseCreateView
    menu_label = _("Data verse")
    menu_icon = "folder"
    menu_order = 200
    add_to_admin_menu = False
    exclude_from_explorer = False


class FileCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class FileAdmin(ModelAdmin):
    model = File
    create_view_class = FileCreateView
    menu_label = _("File")
    menu_icon = "folder"
    menu_order = 300
    add_to_admin_menu = False
    exclude_from_explorer = False


class DataSetAdminGroup(ModelAdminGroup):
    menu_label = _("Data Set")
    menu_icon = "folder-open-inverse"
    menu_order = 300
    items = (DataSetAdmin, DataVerseAdmin, FileAdmin)


modeladmin_register(DataSetAdminGroup)
