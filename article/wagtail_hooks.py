from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from wagtail.contrib.modeladmin.views import CreateView

from article.models import (
    # AbstractModel,
    Article,
    ArticleFunding,
    # Category,
    SubArticle,
    # Title,
)


class ArticleCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ArticleAdmin(ModelAdmin):
    model = Article
    create_view_class = ArticleCreateView
    menu_label = _("Article")
    menu_icon = "folder"
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    def all_fundings(self, obj):
        return " | ".join([str(c) for c in obj.fundings.all()])

    def all_doi(self, obj):
        return " | ".join([str(c.value) for c in obj.doi.all()])

    list_display = ("all_doi", "pid_v2", "all_fundings")
    search_fields = ("pid_v2",)


class SubArticleAdmin(ModelAdmin):
    model = SubArticle
    menu_label = _("SubArticle")
    menu_icon = "folder"
    menu_order = 101
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )

    def all_fundings(self, obj):
        return " | ".join([str(c) for c in obj.fundings.all()])

    list_display = ("pid_v2", "all_fundings")
    search_fields = ("pid_v2",)


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
    menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (ArticleAdmin, ArticleFundingAdmin)


modeladmin_register(ArticleAdminGroup)


# class TitleAdmin(ModelAdmin):
#     model = Title
#     menu_label = _("Title")
#     menu_icon = "folder"
#     menu_order = 300
#     add_to_settings_menu = False
#     exclude_from_explorer = False

#     list_display = ("title",)
#     search_fields = ("title",)


# class AbstractModelAdmin(ModelAdmin):
#     model = AbstractModel
#     menu_label = _("Abstract")
#     menu_icon = "folder"
#     menu_order = 400
#     add_to_settings_menu = False
#     exclude_from_explorer = False

#     list_display = ("text",)
#     search_fields = ("text",)


# class CategoryAdmin(ModelAdmin):
#     model = Category
#     menu_label = _("Category")
#     menu_icon = "folder"
#     menu_order = 500
#     add_to_settings_menu = False
#     exclude_from_explorer = False

#     list_display = ("name",)
#     search_fields = ("name",)
