from journal.models import Journal
from editorialboard.models import EditorialBoard
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
