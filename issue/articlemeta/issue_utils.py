import logging
import sys

from langdetect import detect

from core.models import Language
from tracker.models import UnexpectedEvent


def normalize_markup_done(markup_done):
    val = extract_value(markup_done)
    if val in ("0", 0, None, ""):
        markup_done = False
    elif val in ("1", 1):
        markup_done = True
    else:
        markup_done = False
    return markup_done


def extract_data_from_harvested_data(issue_data, pid):
    volume = issue_data.get("volume")
    number = issue_data.get("number")
    supplement_volume = issue_data.get("supplement_volume")
    supplement_number = issue_data.get("supplement_number")
    data_iso = issue_data.get("date_iso")
    sections_data = issue_data.get("sections_data") or []
    markup_done = issue_data.get("markup_done")

    supplement = extract_value(supplement_number) or extract_value(supplement_volume)
    data = extract_value(data_iso)
    markup_done = normalize_markup_done(markup_done)

    bibliographic_strip_list = []
    for item in issue_data.get("bibliographic_strip") or []:
        """
        {
            "a": "2024",
            "c": "S\u00e3o Paulo",
            "l": "es",
            "t": "Gal\u00e1xia (S\u00e3o Paulo)",
            "v": "vol.49",
            "_": ""
        },
        """
        lang = item.get("l")
        if not lang:
            continue

        bibliographic_strip = {
            "language": lang,
            "title": item.get("t"),
            "volume": item.get("v"),
            "number": item.get("n"),
            "supplement": item.get("s"),
            "city": item.get("c"),
            "season": item.get("m"),  # mes(es) abreviado(s) no idioma indicado,
            "year": item.get("a"),
        }
        bibliographic_strip["text"] = format_bibliographic_strip(bibliographic_strip)
        if not bibliographic_strip["text"]:
            continue
        bibliographic_strip_list.append(bibliographic_strip)

    issue_titles = []
    for item in issue_data.get("issue_title", []):
        """
        {
            "l": "pt",
            "t": "Revista de Teste"
        }
        """
        issue_title = {
            "language": item.get("l"),
            "title": item.get("t") or item.get("_"),
        }
        issue_titles.append(issue_title)
    return {
        "volume": extract_value(volume),
        "number": extract_value(number),
        "supplement": supplement,
        "year": data[:4],
        "month": data[4:6],
        "markup_done": markup_done,
        "order": pid[-4:],
        "issue_pid_suffix": pid[-4:],
        "sections_data": list(fix_section_data(sections_data)),
        "bibliographic_strip_list": bibliographic_strip_list,
        "issue_titles": issue_titles,
    }


def format_bibliographic_strip(bibliographic_strip):
    items = []
    for label in ["title", "volume", "number", "supplement", "city", "season", "year"]:
        if value := bibliographic_strip.get(label):
            items.append(value)
    return ", ".join(items)


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
                if not language:
                    continue
                yield {
                    "c": item.get("c"),
                    "l": language,
                    "t": section_text, # Usar o texto completo mesmo que tenha sido dividido
                }
