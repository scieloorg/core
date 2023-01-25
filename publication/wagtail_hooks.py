from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _

from wagtail.contrib.modeladmin.views import CreateView
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register

from .models import Publication


class PublicationCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class PublicationAdmin(ModelAdmin):
    model = Publication
    create_view_class = PublicationCreateView
    menu_label = _('Publication')
    menu_icon = 'folder'
    menu_order = 800
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('issue', 'pid', 'pub_type', 'title', 'first_page', 'last_page', 'authors')
    search_fields = ('issue', 'pid', 'pub_type', 'title', 'authors')
    list_export = ('issue', 'pid', 'pub_type', 'title', 'first_page', 'last_page', 'authors', 'creator', 'updated', 'created', 'updated_by')
    export_filename = 'publications'


modeladmin_register(PublicationAdmin)
