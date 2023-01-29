from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _

from wagtail.contrib.modeladmin.views import CreateView
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register, ModelAdminGroup

from article.models import Article, ArticleFunding


class ArticleCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ArticleAdmin(ModelAdmin):
    model = Article
    create_view_class = ArticleCreateView
    menu_label = _('Article')
    menu_icon = 'folder'
    menu_order = 100
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('pid_v2', 'funding')
    search_fields = ('pid_v2', 'funding')


class ArticleFundingCreateView(CreateView):

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ArticleFundingAdmin(ModelAdmin):
    model = ArticleFunding
    create_view_class = ArticleFundingCreateView
    menu_label = _('Article Funding')
    menu_icon = 'folder'
    menu_order = 200
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = False  # or True to exclude pages of this type from Wagtail's explorer view
    list_display = ('award_id', 'funding_source')
    search_fields = ('award_id', 'funding_source')


class ArticleAdminGroup(ModelAdminGroup):
    menu_label = _('Articles')
    menu_icon = 'folder-open-inverse'  # change as required
    menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (ArticleAdmin, ArticleFundingAdmin)


modeladmin_register(ArticleAdminGroup)
