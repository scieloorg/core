from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import (
    CreateView,
    SnippetViewSet,
    SnippetViewSetGroup,
)

from config.menu import get_menu_order
from config.settings.base import COLLECTION_TEAM, JOURNAL_TEAM

from .models import Issue


class IssueCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class IssueAdmin(SnippetViewSet):
    model = Issue
    inspect_view_enabled = True
    menu_label = _("Issues")
    add_view_class = IssueCreateView
    menu_icon = "folder-open-inverse"
    menu_order = 150
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "journal",
        "year",        
        "volume",        
        "number",
        "supplement",
        "created",
        "updated",
    )
    list_filter = (
        "year",
        "month",
    )
    search_fields = (
        "journal__title",
        "journal__official__issn_print",
        "journal__official__issn_electronic",
        "number",
        "volume",
        "year",
        "month",
        "supplement",
    )

    def get_queryset(self, request):
        qs = Issue.objects.all()
        user = request.user

        if user.is_superuser:
            return qs

        user_groups = user.groups.values_list("name", flat=True)
        if COLLECTION_TEAM in user_groups:
            collections = getattr(user, "collections", None)
            if collections is not None:
                return qs.filter(
                    journal__scielojournal__collection__in=collections
                )
        elif JOURNAL_TEAM in user_groups:
            journals = getattr(user, "journals", None)
            if journals is not None:
                journals_ids = journals.values_list("id", flat=True)
                return qs.filter(
                    journal__id__in=journals_ids
                )
        return qs.none()


class IssueAdminGroup(SnippetViewSetGroup):
    menu_label = _("Issues")
    menu_icon = "folder-open-inverse"
    menu_order = get_menu_order("issue")
    items = (IssueAdmin, )


register_snippet(IssueAdminGroup)
