from django.urls import path
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from config.menu import get_menu_order
from report.views import visual_element_totals_csv_view, visual_element_totals_view

from .models import ReportCSV

@register_snippet
class ReportCSVAdmin(SnippetViewSet):
    model = ReportCSV
    menu_label = _("Report CSV")
    menu_icon = "folder"
    menu_order = get_menu_order("report")
    add_to_settings_menu = False
    list_display = (
        "journal",
        "title",
        "publication_year",
        "created",
        "updated",
        "link_download"
    )
    list_filter = (
        "publication_year",
        "title",
    )
    
    search_fields = (
        "title",
        "journal__title",
        "journal__scielojournal__issn_scielo",
    )

    def link_download(self, obj):
        if obj.file and obj.file.url:
            return f"<a target='_blank' href={obj.file.url}>Download</a>"
        return None

    link_download.short_descriptions = 'Download'
    link_download.allow_tags = True


@hooks.register("register_admin_urls")
def register_visual_element_totals_urls():
    return [
        path(
            "report/visual-element-totals/",
            visual_element_totals_view,
            name="visual_element_totals",
        ),
        path(
            "report/visual-element-totals/csv/",
            visual_element_totals_csv_view,
            name="visual_element_totals_csv",
        ),
    ]
