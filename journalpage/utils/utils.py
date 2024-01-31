from journal.models import Journal
from editorialboard.models import EditorialBoard
from editorialboard.choices import ROLE
from django.shortcuts import render


def get_journal_by_acronyms(journal_acron, acron_collection):
    return Journal.objects.get(
        scielojournal__journal_acron=journal_acron,
        scielojournal__collection__acron3=acron_collection,
    )
