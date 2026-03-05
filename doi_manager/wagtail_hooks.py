from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.snippets import widgets as wagtailsnippets_widgets
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from config.menu import get_menu_order
from doi_manager.models import CrossRefConfiguration, CrossRefDeposit
from doi_manager.views import deposit_article_to_crossref


class CrossRefConfigurationSnippetViewSet(SnippetViewSet):
    model = CrossRefConfiguration
    menu_label = _("Crossref Configuration")
    menu_icon = "cog"
    menu_order = 100
    list_display = (
        "prefix",
        "depositor_name",
        "depositor_email_address",
        "registrant",
        "use_test_server",
        "updated",
    )
    list_filter = ("use_test_server",)
    search_fields = (
        "prefix",
        "depositor_name",
        "registrant",
    )


class CrossRefDepositSnippetViewSet(SnippetViewSet):
    model = CrossRefDeposit
    menu_label = _("Crossref Deposits")
    menu_icon = "upload"
    menu_order = 200
    list_display = (
        "article",
        "status",
        "submission_date",
        "updated",
    )
    list_filter = ("status",)
    search_fields = (
        "article__sps_pkg_name",
        "article__pid_v3",
        "article__pid_v2",
    )
    ordering = ["-updated"]


class CrossRefSnippetViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Crossref")
    menu_icon = "folder-open-inverse"
    menu_order = get_menu_order("doi_manager")
    items = (
        CrossRefConfigurationSnippetViewSet,
        CrossRefDepositSnippetViewSet,
    )


register_snippet(CrossRefSnippetViewSetGroup)


@hooks.register("register_admin_urls")
def register_doi_manager_urls():
    return [
        path(
            "doi_manager/deposit/<int:article_id>/",
            deposit_article_to_crossref,
            name="crossref_deposit_article",
        ),
    ]


@hooks.register("register_snippet_listing_buttons")
def crossref_deposit_button(snippet, user, next_url=None):
    from article.models import Article

    if isinstance(snippet, Article):
        deposit_url = reverse("crossref_deposit_article", args=[snippet.pk])
        yield wagtailsnippets_widgets.SnippetListingButton(
            _("Deposit DOI to Crossref"),
            deposit_url,
            priority=100,
            icon_name="upload",
            attrs={
                "title": _("Deposit DOI to Crossref"),
                "data-action": "crossref-deposit",
            },
        )

