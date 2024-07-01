from django.shortcuts import render
from django.utils import translation
from django.http import HttpResponseNotFound, JsonResponse
from wagtail.models import Page
from wagtail.contrib.routable_page.models import RoutablePageMixin, re_path

from journal.models import Journal
from journalpage.utils.utils import get_journal_by_acronyms, get_editorial_board, render_journal_page_with_latest_context, verify_journal_is_latest
from core.models import Language
from editorialboard.choices import ROLE


class PageNotVisibleError(Exception):
    pass


class JournalPage(RoutablePageMixin, Page):
    def get_context(self, request, *args, **kwargs):
        # Obter as traduções disponíveis
        available_translations = translation.trans_real.get_languages()
        # Obter o idioma atual
        current_language = translation.get_language()
        language_info = translation.get_language_info(current_language)
        # Adicionar as traduções ao contexto
        context = super().get_context(request, *args, **kwargs)
        context['available_translations'] = available_translations
        context['current_language_name'] = language_info['name']
        return context

    @re_path(r"^(?P<collection_acron3>[\w-]+)/(?P<acron>[\w-]+)/$", name="bibliographic")
    def journal_bibliographic_info_page(self, request, collection_acron3, acron):
        language = request.LANGUAGE_CODE
        context = self.get_context(request)
        page = context['self']
        language = Language.get_or_create(code2=language)

        try:
            journal = get_journal_by_acronyms(acron_collection=collection_acron3, journal_acron=acron)
        except Journal.DoesNotExist:
            return HttpResponseNotFound("Journal not found")
        
        if not journal.valid:
            response_data = {"error": type(PageNotVisibleError()).__name__}
            return JsonResponse(response_data)

        try:
            verify_journal_is_latest(journal=journal)
        except AssertionError:
            return render_journal_page_with_latest_context(self, request, journal=journal, page=page, context=context)

        acron_journal = journal.scielojournal_set.all()[0].journal_acron
        acron_collection = journal.scielojournal_set.all()[0].collection.acron3        
        editorial_board = get_editorial_board(journal=journal)

        mission = journal.mission.get_object_in_preferred_language(language=language)
        brief_history = journal.history.get_object_in_preferred_language(language=language)
        focus_and_scope = journal.focus.get_object_in_preferred_language(language=language)
        social_network = journal.journalsocialnetwork.all()
        preprint = journal.preprint.get_object_in_preferred_language(language=language)
        open_data = journal.open_data.get_object_in_preferred_language(language=language)
        review = journal.review.get_object_in_preferred_language(language=language)
        ecommittee = journal.ecommittee.get_object_in_preferred_language(language=language)
        copyright = journal.copyright.get_object_in_preferred_language(language=language)
        website_responsibility = journal.website_responsibility.get_object_in_preferred_language(language=language)
        author_responsibility = journal.author_responsibility.get_object_in_preferred_language(language=language)
        policies = journal.policies.get_object_in_preferred_language(language=language)
        conflict_policy = journal.conflict_policy.get_object_in_preferred_language(language=language)
        gender_issues = journal.gender_issues.get_object_in_preferred_language(language=language)
        accepted_documment_types = journal.accepted_documment_types.get_object_in_preferred_language(language=language)
        authors_contributions = journal.authors_contributions.get_object_in_preferred_language(language=language)
        digital_assets = journal.digital_assets.get_object_in_preferred_language(language=language)
        citations_and_references = journal.citations_and_references.get_object_in_preferred_language(language=language)
        supp_docs_submission = journal.supp_docs_submission.get_object_in_preferred_language(language=language)
        financing_statement = journal.financing_statement.get_object_in_preferred_language(language=language)
        acknowledgements = journal.acknowledgements.get_object_in_preferred_language(language=language)
        additional_information = journal.additional_information.get_object_in_preferred_language(language=language)
        digital_preservation = journal.digital_preservation.get_object_in_preferred_language(language=language)
        ethics = journal.ethics.get_object_in_preferred_language(language=language)
        fee_charging = journal.fee_charging.get_object_in_preferred_language(language=language)
        sponsor_history = journal.sponsor_history.all()

        context = {
            "journal": journal,
            "mission": mission,
            "brief_history" : brief_history,
            "focus_and_scope": focus_and_scope,
            "social_network": social_network,
            "preprint": preprint,
            "open_data": open_data,
            "review": review,
            "ecommittee": ecommittee,
            "copyright": copyright,
            "website_responsibility": website_responsibility,
            "author_responsibility": author_responsibility,
            "policies": policies,
            "conflict_policy": conflict_policy,
            "gender_issues": gender_issues,
            "accepted_documment_types": accepted_documment_types,
            "authors_contributions": authors_contributions,
            "digital_assets": digital_assets,
            "citations_and_references": citations_and_references,
            "supp_docs_submission": supp_docs_submission,
            "financing_statement": financing_statement,
            "acknowledgements": acknowledgements,
            "additional_information": additional_information,
            "digital_preservation": digital_preservation,
            "ethics": ethics,
            "fee_charging": fee_charging,
            "sponsor_history": sponsor_history,
            "editorial_board": editorial_board,
            "role_editorial_board": ROLE,
            # Current e available language 
            "language": str(self.locale),
            "translations": context["available_translations"],
            "page": page,
            "acron_collection": acron_collection,
            "acron_journal": acron_journal,
        }
        return render(request, "journalpage/about.html", context)
