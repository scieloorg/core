from django.http import HttpResponseRedirect
from wagtail.snippets.views.snippets import SnippetViewSet


class CommonControlFieldViewSet(SnippetViewSet):
    """ViewSet base com save_instance compartilhado"""
    
    def save_instance(self, instance, form, is_new):
        if hasattr(form, 'save_all'):
            return form.save_all(self.request.user)
        return super().save_instance(instance, form, is_new)