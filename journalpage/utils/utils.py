from journal.models import Journal
from editorialboard.models import EditorialBoardMember
from editorialboard.choices import ROLE
from django.shortcuts import render

from collections import defaultdict

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


def get_editorial_board_with_role(journal):
    try:
        editorial_board_by_latest_role = defaultdict(list)
        editorial_board_members = EditorialBoardMember.objects.filter(journal=journal) \
            .prefetch_related(
                "role_editorial_board", 
                "researcher__orcid", 
                "researcher__affiliation__location"
            )
        for member in editorial_board_members:
            role = member.role_editorial_board.order_by("-initial_year").first()
            if role and role.role: 
                lattes = member.researcher.researcher_ids.filter(source_name="LATTES")
                lattes = lattes.first().identifier if lattes.exists() else None
                orcid = member.researcher.orcid.orcid if member.researcher.orcid else None

                editorial_board_by_latest_role[role.role.std_role].append({
                    "researcher": member.researcher,
                    "researcher_affiliation": member.researcher.affiliation,
                    "researcher_orcid": orcid,
                    "researcher_lattes": lattes,
                })
    except Exception:
        editorial_board_by_latest_role = None

    return editorial_board_by_latest_role


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