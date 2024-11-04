import logging

from core.models import Language
from journal.models import SciELOJournal

from ..models import Issue, TocSection


def get_or_create_issue(
    issn_scielo,
    volume,
    number,
    data_iso,
    supplement_volume,
    supplement_number,
    sections_data,
    user,
):
    scielo_journal = get_scielo_journal(issn_scielo)
    supplement = extract_value(supplement_number) or extract_value(supplement_volume)
    data = extract_value(data_iso)

    obj = Issue.get_or_create(
        journal=scielo_journal.journal,
        volume=extract_value(volume),
        number=extract_value(number),
        supplement=supplement,
        year=data[:4],
        month=data[4:6],
        sections=get_or_create_sections(sections_data, user),
        user=user,
        season=None,
    )


def get_scielo_journal(issn_scielo):
    try:
        issn_scielo = extract_value(issn_scielo)
        return SciELOJournal.objects.get(issn_scielo=issn_scielo)
    except SciELOJournal.DoesNotExist:
        logging.exception(f"Nenhum SciELOJournal encontrado com ISSN: {issn_scielo}")
        return None
    except SciELOJournal.MultipleObjectsReturned:
        return SciELOJournal.objects.filter(issn_scielo=issn_scielo).first()


def extract_date(date):
    if date:
        return [(x.get("a"), x.get("m")) for x in date][0]
    return None, None


def extract_value_sections_data(sections):
    """
    "v49": [
      {
        "c": "BJID020",
        "l": "en",
        "_": "",
        "t": "Case Report"
      },
      {
        "c": "BJID010",
        "l": "en",
        "_": "",
        "t": "Original Papers"
      }
    ]
    """
    return [
        {
            "lang": x.get("l"),
            "section": x.get("t"),
        }
        for x in sections
    ]


def get_or_create_sections(sections, user):
    data = []
    if sections and isinstance(sections, list):
        sections = extract_value_sections_data(sections=sections)
        for section in sections:
            obj, create = TocSection.objects.get_or_create(
                plain_text=section.get("section"),
                language=Language.get_or_create(
                    code2=section.get("lang"),
                ),
                creator=user,
            )
            data.append(obj)
    return data


def extract_value(value):
    if value and isinstance(value, list):
        return [x.get("_") for x in value][0]
