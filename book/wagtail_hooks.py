from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from book.models import Book


class BookCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class BookAdmin(ModelAdmin):
    model = Book
    create_view_class = BookCreateView
    menu_label = _("Books")
    menu_icon = "folder"
    menu_order = 900
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    list_display = (
        "title",
        "synopsis",
        "isbn",
        "eisbn",
        "doi",
        "year",
        "language",
        "location",
        "institution",
    )
    search_fields = ("doi", "title", "isbn", "eisbn", "synopsis")


class BookAdminGroup(ModelAdminGroup):
    menu_label = _("Books")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = 5  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (BookAdmin,)


modeladmin_register(BookAdminGroup)
