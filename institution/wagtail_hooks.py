from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _

from wagtail.contrib.modeladmin.views import CreateView
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register

from .models import Institution


class InstitutionCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class InstitutionAdmin(ModelAdmin):
    model = Institution
    create_view_class = InstitutionCreateView
    menu_label = _('Institution')
    menu_icon = 'folder'
    menu_order = 300
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('name', 'institution_type', 'creator', 'updated', 'created', 'updated_by')
    search_fields = ('name', 'institution_type', 'creator', 'updated', 'created', 'updated_by')
    list_export = ('name', 'institution_type', 'level_1', 'level_2', 'level_3', 'creator', 'updated', 'created', 'updated_by')
    export_filename = 'institutions'


modeladmin_register(InstitutionAdmin)
