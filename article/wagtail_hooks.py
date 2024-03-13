from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from article.models import (  # AbstractModel,; Category,; Title,
    Article,
    ArticleFormat,
    ArticleFunding,
)
from core.wagtail_hooks import BaseEditView


class ArticleCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ArticleEditView(BaseEditView):
    readonly_fields = [
        "pid_v2",
        "pid_v3",
        "journal",
        "doi",
        "publisher",
    ]


class ArticleAdmin(ModelAdmin):
    model = Article
    create_view_class = ArticleCreateView
    edit_view_class = ArticleEditView
    menu_label = _("Article")
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    list_display = (
        "sps_pkg_name",
        "doi",
        "pid_v3",
        "pid_v2",
        "valid",
        "created",
        "updated",
    )
    list_filter = ("valid",)
    search_fields = (
        "titles__plain_text",
        "pid_v2",
        "doi__value",
        "sps_pkg_name",
        "pid_v3",
    )


class ArticleFormatCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ArticleFormatAdmin(ModelAdmin):
    model = ArticleFormat
    create_view_class = ArticleFormatCreateView
    menu_label = _("Article Format")
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    list_display = (
        "article",
        "format_name",
        "version",
        "valid",
        "created",
        "updated",
    )
    list_filter = ("format_name", "version", "valid")
    search_fields = (
        "article__sps_pkg_name",
        "format_name",
        "version",
    )


class ArticleFundingCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ArticleFundingAdmin(ModelAdmin):
    model = ArticleFunding
    create_view_class = ArticleFundingCreateView
    menu_label = _("Article Funding")
    menu_icon = "folder"
    menu_order = 200
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    list_display = ("award_id", "funding_source")
    search_fields = (
        "award_id",
        "funding_source__name",
        "funding_source__institution_type",
    )


class ArticleAdminGroup(ModelAdminGroup):
    menu_label = _("Articles")
    menu_icon = "folder-open-inverse"  # change as required
    menu_order = 4  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (ArticleAdmin, ArticleFormatAdmin, ArticleFundingAdmin)


modeladmin_register(ArticleAdminGroup)
