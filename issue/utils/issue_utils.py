import logging
import sys

from django.db import IntegrityError, transaction

from core.models import Language
from tracker.models import UnexpectedEvent

from issue.models import CodeSectionIssue, Issue, SectionIssue, TocSection


def normalize_markup_done(markup_done):
    val = extract_value(markup_done)
    if val in ("0", 0, None, ""):
        markup_done = False
    elif val in ("1", 1):
        markup_done = True
    else:
        markup_done = False
    return markup_done


def get_or_create_issue(
    journal,
    volume,
    number,
    data_iso,
    supplement_volume,
    supplement_number,
    sections_data,
    markup_done,
    user,
    order=None,
    issue_pid_suffix=None,    
):
    supplement = extract_value(supplement_number) or extract_value(supplement_volume)
    data = extract_value(data_iso)
    
    markup_done = normalize_markup_done(markup_done)

    obj = Issue.get_or_create(
        journal=journal,
        volume=extract_value(volume),
        number=extract_value(number),
        supplement=supplement,
        year=data[:4],
        month=data[4:6],
        sections=get_or_create_sections(sections_data, user),
        markup_done=markup_done,
        order=order,
        issue_pid_suffix=issue_pid_suffix,
        user=user,
        season=None,
    )
    data_code_sections = get_or_create_code_sections(sections_data, user)
    for section in data_code_sections:
        obj.code_sections.add(section)

    return obj


def extract_date(date):
    if date:
        return [(x.get("a"), x.get("m")) for x in date][0]
    return None, None


def get_or_create_sections(sections, user):
    data = []
    if sections and isinstance(sections, list):
        for section in sections:
            text = section.get("t", "")
            lang_code2 = section.get("l")
            language = Language.get_or_create(code2=lang_code2, creator=user)
            try:
                with transaction.atomic():
                    obj, _ = TocSection.objects.get_or_create(
                        plain_text=text,
                        language=language,
                        defaults={
                            "creator": user,
                        }
                    )
            except IntegrityError as e:
                obj, _ = TocSection.objects.get(
                    plain_text=text,
                    language=language,
                )
            data.append(obj)
    return data


def extract_value(value):
    if value and isinstance(value, list):
        return [x.get("_") for x in value][0]


def get_or_create_code_sections(sections_data, user):
    data = []
    if sections_data and isinstance(sections_data, list):
        for section in sections_data:
            code = section.get("c")
            lang_code2 = section.get("l")
            text = section.get("t", "")
            try:
                code_section, _ = CodeSectionIssue.objects.get_or_create(
                    code=code,
                    defaults={
                        "creator": user,
                    }
                )
                language = Language.get_or_create(code2=lang_code2, creator=user)
                try:
                    with transaction.atomic():
                        issue_section, _ = SectionIssue.objects.get_or_create(
                            code_section=code_section,
                            language=language,
                            defaults={
                                "text": text,
                                "creator": user,
                            }
                        )
                except IntegrityError as e:
                    issue_section, _ = SectionIssue.objects.get(
                        code_section=code_section,
                        language=language,
                    )
                data.append(issue_section)
            except Exception as e:
                logging.error(f"Erro ao criar section_issue: {e}")
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=e,
                    exc_traceback=exc_traceback,
                    detail={
                        "function": "get_or_create_code_sections",
                        "section": section,
                    },
                )
    return data

