from django.http import HttpResponseRedirect
from wagtail_modeladmin.views import CreateView


class CommonControlFieldCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())
