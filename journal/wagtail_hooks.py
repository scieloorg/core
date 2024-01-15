from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.translation import gettext as _
from wagtail import hooks
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from . import models
from .button_helper import IndexedAtHelper
from .views import import_file, validate


class OfficialJournalCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class OfficialJournalAdmin(ModelAdmin):
    model = models.OfficialJournal
    inspect_view_enabled = True
    menu_label = _("ISSN Journals")
    create_view_class = OfficialJournalCreateView
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "title",
        "initial_year",
        "terminate_year",
        "issn_print",
        "issn_electronic",
        "issnl",
        "created",
        "updated",
    )
    list_filter = ("terminate_year", "initial_year",)
    search_fields = (
        "title",
        "initial_year",
        "issn_print",
        "issn_electronic",
        "issnl",
    )


class JournalCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class JournalAdmin(ModelAdmin):
    model = models.Journal
    inspect_view_enabled = True
    menu_label = _("Journals")
    create_view_class = JournalCreateView
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_per_page = 20

    list_display = (
        "title",
        "contact_location",
        "created",
        "updated",
    )
    list_filter = (
        "use_license",
        "publishing_model",
        "subject",
        "main_collection",
    )
    search_fields = (
        "title",
        "official__issn_print",
        "official__issn_electronic",
        "contact_location__country__name",
    )
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user_groups = request.user.groups.values_list('name', flat=True)
        if 'Equipe de Coordenação da Coleção' in user_groups:
            return qs.filter(scielojournal__collection__in=request.user.collection.all())
        elif 'Equipe Editorial do Periódico' in user_groups:
            return qs.filter(id=request.user.journal.id)
        return qs
    

class SciELOJournalCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class SciELOJournalAdmin(ModelAdmin):
    model = models.SciELOJournal
    inspect_view_enabled = True
    menu_label = _("SciELO Journals")
    create_view_class = SciELOJournalCreateView
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False

    list_display = (
        "journal",
        "issn_scielo",
        "journal_acron",
        "collection",
        "status",
        "created",
        "updated",
    )
    list_filter = ("status", "collection", )
    search_fields = (
        "journal_acron",
        "journal__title",
        "issn_scielo",
    )
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user_groups = request.user.groups.values_list('name', flat=True)
        if 'Equipe de Coordenação da Coleção' in user_groups:
            return qs.filter(collection__in=request.user.collection.all())
        elif 'Equipe Editorial do Periódico' in user_groups:
            return qs.filter(journal=request.user.journal)
        return qs


class JournalAdminGroup(ModelAdminGroup):
    menu_label = _("Journals")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = 2
    items = (JournalAdmin, OfficialJournalAdmin, SciELOJournalAdmin)


modeladmin_register(JournalAdminGroup)


class IndexedAtAdmin(ModelAdmin):
    model = models.IndexedAt
    menu_label = "Indexed At"
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ("name", "acronym", "url", "description", "type")
    list_filter = ("type",)
    search_fields = ("name", "acronym")
    list_export = ("name", "acronym", "url", "description", "type")
    export_filename = "indexed_at"


class IndexedAtFileAdmin(ModelAdmin):
    model = models.IndexedAtFile
    button_helper_class = IndexedAtHelper
    menu_label = "Indexed At Upload"
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ("attachment", "line_count", "is_valid")
    list_filter = ("is_valid",)
    search_fields = ("attachment",)


class IndexedAtAdminGroup(ModelAdminGroup):
    menu_label = "Indexed At"
    menu_icon = "folder-open-inverse"
    menu_order = 200
    items = (
        IndexedAtAdmin,
        IndexedAtFileAdmin,
    )


# modeladmin_register(IndexedAtAdminGroup)

class WebOfKnowledgeAdmin(ModelAdmin):
    model = models.WebOfKnowledge
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "code",
        "value",
    )

    search_fields = (
        "code",
        "value",
    )


class SubjectAdmin(ModelAdmin):
    model = models.Subject
    menu_icon = "folder"
    menu_order = 300
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "code",
        "value",
    )

    search_fields = (
        "code",
        "value",
    )


class WosAreaAdmin(ModelAdmin):
    model = models.WebOfKnowledgeSubjectCategory
    menu_icon = "folder"
    menu_order = 400
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "value",
    )
    search_fields = (
        "value",
    )    

class ListCodesAdminGroup(ModelAdminGroup):
    menu_label = "List of codes"
    menu_icon = "folder-open-inverse"
    menu_order = 1100
    items = (
        SubjectAdmin,
        WebOfKnowledgeAdmin,
        WosAreaAdmin,
    )

modeladmin_register(ListCodesAdminGroup)

# TODO
# Futuramente mudar para JournalAdminGroup 
# com permissoes de visualizacao restrita
class AMJournalAdmin(ModelAdmin):
    model = models.AMJournal
    menu_label = "AM Journal"
    menu_icon = "folder"
    menu_order = 1200
    list_display = ("scielo_issn", "collection") 
    list_filter = ("collection",)
    search_fields = ("scielo_issn",)

class ArticleSubmissionFormatCheckListAdmin(ModelAdmin):
    model = models.ArticleSubmissionFormatCheckList
    menu_label = _("Article Submission Format Check List")
    menu_icon = "folder"
    menu_order = 1200

modeladmin_register(AMJournalAdmin)
modeladmin_register(ArticleSubmissionFormatCheckListAdmin)


@hooks.register("register_admin_urls")
def register_calendar_url():
    return [
        path(
            "controlled_lists/indexedatfile/validate",
            validate,
            name="validate",
        ),
        path(
            "controlled_lists/indexedatfile/import_file",
            import_file,
            name="import_file",
        ),
    ]
