from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.translation import gettext as _
from wagtail import hooks
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from . import models


class JournalTOCCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class JournalTOCAdmin(ModelAdmin):
    model = models.JournalTOC
    menu_label = _("JournalTOC")
    menu_icon = "folder"
    menu_order = 200
    create_view_class = JournalTOCCreateView
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ("journal",)
    search_fields = ("journal",)


class IssueTOCAdmin(ModelAdmin):
    model = models.IssueTOC
    menu_label = _("IssueTOC")
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = ("issue",)
    search_fields = ("issue",)


modeladmin_register(JournalTOCAdmin)
modeladmin_register(IssueTOCAdmin)