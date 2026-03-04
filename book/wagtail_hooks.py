from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import CreateView, SnippetViewSet, SnippetViewSetGroup

from book.models import Book
from config.menu import get_menu_order


class BookCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class BookAdmin(SnippetViewSet):
    model = Book
    add_view_class = BookCreateView
    menu_label = _("Books")
    menu_icon = "folder"
    menu_order = 900
    add_to_settings_menu = False

    list_display = (
        "title",
        "synopsis",
        "isbn",
        "eisbn",
        "doi",
        "year",
        "language",
        "location",
        "publisher",
    )
    search_fields = ("doi", "title", "isbn", "eisbn", "synopsis")


class BookAdminGroup(SnippetViewSetGroup):
    menu_label = _("Books")
    menu_icon = "folder-open-inverse"
    menu_order = get_menu_order("book")
    items = (BookAdmin,)


register_snippet(BookAdminGroup)
