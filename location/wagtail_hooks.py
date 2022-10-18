from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _

from wagtail.contrib.modeladmin.views import CreateView
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register

from .models import Location


class LocationCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class LocationAdmin(ModelAdmin):
    model = Location
    create_view_class = LocationCreateView
    menu_label = _('Location')
    menu_icon = 'folder'
    menu_order = 300
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('country', 'state', 'city', 'creator',
                    'updated', 'created', )
    search_fields = ('country', 'state', 'city', )
    list_export = ('country', 'state', 'city', )
    export_filename = 'locations'

modeladmin_register(LocationAdmin)
