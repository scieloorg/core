import logging
import sys

from django.db import IntegrityError, transaction
from langdetect import detect

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
    collection,
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
        markup_done=markup_done,
        order=order,
        issue_pid_suffix=issue_pid_suffix,
        user=user,
        season=None,
    )
    obj.add_sections(user, fix_section_data(sections_data), collection)

    return obj


def extract_date(date):
    if date:
        return [(x.get("a"), x.get("m")) for x in date][0]
    return None, None


def extract_value(value):
    if value and isinstance(value, list):
        return [x.get("_") for x in value][0]


def fix_section_data(sections_data):        
    for item in sections_data:
        section_text = item.get("t")
        if not section_text:
            continue
        lang_code2 = item.get("l")
        if not lang_code2:
            continue

        try:
            language = Language.get(lang_code2)
            yield {
                "c": item.get("c"),
                "l": language,
                "t": section_text,
            }
        except Language.DoesNotExist:
            for text in section_text.split("/"):
                text = text.strip()
                if not text:
                    continue
                language = None
                try:
                    detected_lang = detect(text)
                    language = Language.get(detected_lang)
                except Language.DoesNotExist:
                    language = Language.get("en")
                finally:
                    if not language:
                        continue
                    yield {
                        "c": item.get("c"),
                        "l": language,
                        "t": section_text,
                    }
