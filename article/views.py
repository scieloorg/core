from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from wagtail_modeladmin.views import EditView


class ArticleFormatView(EditView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())

