from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import (
    CreateView,
    SnippetViewSet,
    SnippetViewSetGroup,
)


from .models import Issue, IssueExport
from config.menu import get_menu_order
from config.settings.base import COLLECTION_TEAM, JOURNAL_TEAM

from .models import Issue


class IssueCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class IssueAdminSnippetViewSet(SnippetViewSet):
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
        qs = Issue.objects
        user = request.user

        if user.is_superuser:
            return qs.all()

        user_groups = set(user.groups.values_list("name", flat=True))
        if COLLECTION_TEAM in user_groups:
            collections = getattr(user, "collections", None)
            if collections is not None:
                return qs.filter(
                    journal__scielojournal__collection__in=collections
                ).select_related("journal")
        elif JOURNAL_TEAM in user_groups:
            journals = getattr(user, "journals", None)
            if journals is not None:
                journals_ids = journals.values_list("id", flat=True)
                return qs.filter(
                    journal__id__in=journals_ids
                ).select_related("journal")
        return qs.none()



class IssueExportCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class IssueExportAdmin(SnippetViewSet):
    model = IssueExport
    add_view_class = IssueExportCreateView
    inspect_view_enabled = True
    menu_label = _("Issue Exports")
    menu_icon = "download"
    menu_order = 160
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "issue",
        "export_type",
        "collection",
        "created",
        "updated",
    )
    list_filter = (
        "export_type",
        "collection",
    )
    search_fields = (
        "issue__journal__title",
        "issue__number",
        "issue__volume",
        "issue__year",
    )


class IssueAdminSnippetViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Issues")
    menu_icon = "folder-open-inverse"
    menu_order = get_menu_order("issue")
    items = (IssueAdminSnippetViewSet, IssueExportAdmin)


register_snippet(IssueAdminSnippetViewSetGroup)