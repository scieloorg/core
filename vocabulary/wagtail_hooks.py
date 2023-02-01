from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register, ModelAdminGroup
from wagtail.contrib.modeladmin.views import CreateView

from .models import Vocabulary, Keyword


class VocabularyCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class VocabularyAdmin(ModelAdmin):
    model = Vocabulary
    inspect_view_enabled = True
    menu_label = _('Vocabulary')
    create_view_class = VocabularyCreateView
    menu_icon = 'folder'
    menu_order = 100
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        'name ',
        'acronym',
    )
    list_filter = (
        'name',
    )
    search_fields = (
        'name ',
        'acronym',
    )


class KeywordCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class KeywordAdmin(ModelAdmin):
    model = Keyword
    inspect_view_enabled = True
    menu_label = _('Keyword')
    create_view_class = KeywordCreateView
    menu_icon = 'folder'
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        'text',
        'language',
        'vocabulary',
    )
    list_filter = (
        'language',
    )
    search_fields = (
        'language',
        'vocabulary',
    )


class VocabularyGroup(ModelAdminGroup):
    menu_label = _('Vocabulary')
    menu_icon = 'folder-open-inverse'  # change as required
    menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (VocabularyAdmin, KeywordAdmin)


modeladmin_register(VocabularyGroup)
