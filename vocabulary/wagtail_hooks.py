from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import CreateView, SnippetViewSet, SnippetViewSetGroup
from config.menu import get_menu_order

from .models import Keyword, Vocabulary


class VocabularyCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class VocabularyAdmin(SnippetViewSet):
    model = Vocabulary
    inspect_view_enabled = True
    menu_label = _("Vocabulary")
    add_view_class = VocabularyCreateView
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False

    list_display = (
        "name",
        "acronym",
    )
    search_fields = (
        "name",
        "acronym",
    )


class KeywordCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class KeywordAdmin(SnippetViewSet):
    model = Keyword
    inspect_view_enabled = True
    menu_label = _("Keyword")
    add_view_class = KeywordCreateView
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False

    list_display = (
        "text",
        "language",
        "vocabulary",
    )
    list_filter = ("language", "vocabulary",)
    search_fields = (
        "language__code2",
        "vocabulary__name",
    )
