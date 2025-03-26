from journal.models import Journal
from editorialboard.models import EditorialBoardMember
from editorialboard.choices import ROLE
from django.shortcuts import render


def get_journal_by_acronyms(journal_acron, acron_collection):
    return Journal.objects.get(
        scielojournal__journal_acron=journal_acron,
        scielojournal__collection__acron3=acron_collection,
    )

def find_most_recent_journal(journal):
    # TODO
    # Por enquanto, enquanto os campos old_title e new_title nao estao com valores corretos,
    # esta funcao ira pegar o valor de next_journal_title
    while journal.official.next_journal_title:
        try:
            journal = Journal.objects.get(title=journal.official.next_journal_title)
        except Journal.DoesNotExist:
            break
    return journal


def get_editorial_board(journal):
    try:
        editorial_board = EditorialBoardMember.objects.filter(journal=journal).latest(
            "initial_year"
        )
    except EditorialBoardMember.DoesNotExist:
        editorial_board = None
    return editorial_board


def verify_journal_is_latest(journal):
    most_recent_journal = find_most_recent_journal(journal=journal)
    assert journal == most_recent_journal


def render_journal_page_with_latest_context(self, request, journal, page, context):
    most_recent_journal = find_most_recent_journal(journal=journal)
    context = {
        "journal": journal,
        "most_recent_journal": most_recent_journal,
        "acron_collection": most_recent_journal.scielojournal_set.all()[0].collection.acron3,
        "acron_journal": most_recent_journal.scielojournal_set.all()[0].journal_acron,
        "page": page,
        "translation": context["available_translations"],
        "language": str(self.locale),
    }
    return render(request, "journalpage/next_journal.html", context)