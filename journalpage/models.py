from django.shortcuts import render
from django.http import HttpResponseNotFound
from wagtail.models import Page
from wagtail.contrib.routable_page.models import RoutablePageMixin, re_path

from journal.models import Journal


class JournalPage(RoutablePageMixin, Page):
    @re_path(r"^(?P<acron>[\w-]+)/$", name="bibliographic")
    def journal_bibliographic_info_page(self, request, acron):
        language = request.LANGUAGE_CODE
        context = self.get_context(request)
        # tratar error de get
        try:
            journal = Journal.objects.get(scielojournal__journal_acron=acron)
        except Journal.DoesNotExist:
            return HttpResponseNotFound()
        
        context = {
            "journal": journal,
            "language": language,
            # "translations": context["translations"],
        }
        return self.render(request, "journalpage/journal_page.html", context)
