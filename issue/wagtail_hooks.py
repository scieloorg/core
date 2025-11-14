from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import (
    CreateView,
    SnippetViewSet,
    SnippetViewSetGroup,
)

from config.menu import get_menu_order
from issue.models import Issue, IssueExporter, AMIssue


class AMIssueAdminViewSet(SnippetViewSet):

    model = AMIssue
    inspect_view_enabled = True
    menu_label = _("ArticleMeta Issue")
    # add_view_class = AMIssueCreateView
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "pid",
        "collection",
        "new_record",
        "status",
        "processing_date",
        "updated",
    )
    list_filter = (
        "status",
        "collection",
        "new_record__year",
    )
    search_fields = (
        "pid",
        "processing_date",
        "new_record__journal__title",
        "new_record__journal__scielojournal__journal_acron",
        "new_record__year",
        "new_record__volume",
    )
    # Deve ficar disponível somente para ADM


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
        "short_identification",
        "journal",
        "year",
        "issue_folder"
        "total_articles",
        "updated",
        "updated_by",
        "created",
        "creator",
    )
    list_filter = (
        "journal__scielojournal__collection",
        "year",
    )
    search_fields = (
        "journal__title",
        "journal__official__issn_print",
        "journal__official__issn_electronic",
        "issue_folder",
        "year",
    )

    def get_queryset(self, request):
        # Base queryset com otimizações
        qs = Issue.objects.select_related(
            "journal",
        )
        
        user = request.user
        
        # Verificação de autenticação
        if not user.is_authenticated:
            return qs.none()

        if user.is_superuser:
            return qs.all()

        # Usar as novas properties do modelo User
        if user.has_collection_permission and user.collection_ids:
            return qs.filter(
                journal__scielojournal__collection__id__in=user.collection_ids
            ).distinct()
            
        if user.has_journal_permission and user.journal_ids:
            return qs.filter(
                journal__id__in=user.journal_ids
            ).distinct()
        
        return qs.none()


class IssueExporterCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class IssueExporterAdmin(SnippetViewSet):
    model = IssueExporter
    add_view_class = IssueExporterCreateView
    inspect_view_enabled = True
    menu_label = _("Issue Exports")
    menu_icon = "folder-open-inverse"
    menu_order = 160
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "parent",
        "status",
        "collection",
        "destination",
        "updated",
    )
    list_filter = (
        "collection",
        "status",
        "destination",
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
    items = (
        IssueAdminSnippetViewSet,
        AMIssueAdminViewSet,
        IssueExporterAdmin,
    )


register_snippet(IssueAdminSnippetViewSetGroup)
