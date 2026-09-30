from article.models import Article, ArticleCount, ArticleCountType
from django.db.models import Exists, OuterRef, Q, Sum
from django.db.models.functions import Coalesce
from journal.models import SciELOJournal, ThematicAreaJournal

THEMATIC_AREA_SEPARATOR = "; "
SPREADSHEET_LANGS = ("en", "es", "pt")


def _spreadsheet_columns():
    columns = ["collection", "thematic_area", "journal", "year"]
    for code in ArticleCountType.VISUAL_TYPES:
        for lang in SPREADSHEET_LANGS:
            columns.append(f"{code}-{lang}")
        columns.append(f"{code}_total")
    return tuple(columns)


SPREADSHEET_COLUMNS = _spreadsheet_columns()


def _count_alias(code, lang=None):
    safe = code.replace("-", "_")
    if lang is None:
        return f"{safe}_total"
    return f"{safe}_{lang}"


def _sum_count(code, lang=None):
    condition = Q(count_type__code=code)
    if lang is not None:
        condition &= Q(language__code2=lang)
    return Coalesce(Sum("count", filter=condition), 0)


def _spreadsheet_annotations():
    annotations = {}
    for code in ArticleCountType.VISUAL_TYPES:
        for lang in SPREADSHEET_LANGS:
            annotations[_count_alias(code, lang)] = _sum_count(code, lang)
        annotations[_count_alias(code)] = _sum_count(code)
    return annotations


def filtered_article_ids(collection=None, thematic_area=None, journal=None, pid=None):
    qs = Article.objects.filter(journal__isnull=False)
    if collection:
        qs = qs.filter(
            Exists(
                SciELOJournal.objects.filter(
                    journal_id=OuterRef("journal_id"),
                    collection=collection,
                )
            )
        )
    if thematic_area:
        qs = qs.filter(
            Exists(
                ThematicAreaJournal.objects.filter(
                    journal_id=OuterRef("journal_id"),
                    thematic_area=thematic_area,
                )
            )
        )
    if journal:
        qs = qs.filter(journal=journal)
    if pid:
        pid = pid.strip()
        qs = qs.filter(Q(pid_v2=pid) | Q(pid_v3=pid))
    return qs.values_list("id", flat=True)


def yearly_totals(article_ids):
    return (
        ArticleCount.objects.filter(
            article_id__in=article_ids,
            count_type__code__in=ArticleCountType.VISUAL_TYPES,
        )
        .values("article__pub_date_year")
        .annotate(
            **{
                code.replace("-", "_"): _sum_count(code)
                for code in ArticleCountType.VISUAL_TYPES
            }
        )
        .order_by("-article__pub_date_year")
    )


def _collections_by_journal(journal_ids):
    collections_by_journal = {}
    rows = (
        SciELOJournal.objects.filter(
            journal_id__in=journal_ids,
            collection__acron3__gt="",
        )
        .order_by("collection__acron3")
        .values_list("journal_id", "collection__acron3")
        .distinct()
    )
    for journal_id, acron in rows:
        collections_by_journal.setdefault(journal_id, []).append(acron)
    return collections_by_journal


def _thematic_areas_by_journal(journal_ids):
    areas_by_journal = {}
    items = ThematicAreaJournal.objects.filter(
        journal_id__in=journal_ids,
        thematic_area__isnull=False,
    ).select_related("thematic_area")
    for item in items:
        areas_by_journal.setdefault(item.journal_id, []).append(str(item.thematic_area))
    return areas_by_journal


def spreadsheet_rows(article_ids, collection=None):
    aggregated = list(
        ArticleCount.objects.filter(
            article_id__in=article_ids,
            count_type__code__in=ArticleCountType.VISUAL_TYPES,
        )
        .values(
            "article__journal_id",
            "article__journal__title",
            "article__pub_date_year",
        )
        .annotate(**_spreadsheet_annotations())
    )

    journal_ids = {row["article__journal_id"] for row in aggregated}
    areas_by_journal = _thematic_areas_by_journal(journal_ids)
    collections_by_journal = _collections_by_journal(journal_ids)

    rows = []
    for row in aggregated:
        journal_id = row["article__journal_id"]
        if collection:
            collection_label = collection.acron3
        else:
            collection_label = THEMATIC_AREA_SEPARATOR.join(
                collections_by_journal.get(journal_id, [])
            )
        item = {
            "collection": collection_label,
            "thematic_area": THEMATIC_AREA_SEPARATOR.join(
                areas_by_journal.get(journal_id, [])
            ),
            "journal": row["article__journal__title"],
            "year": row["article__pub_date_year"],
        }
        for code in ArticleCountType.VISUAL_TYPES:
            for lang in SPREADSHEET_LANGS:
                item[f"{code}-{lang}"] = row[_count_alias(code, lang)]
            item[f"{code}_total"] = row[_count_alias(code)]
        rows.append(item)

    return sorted(
        rows,
        key=lambda row: (
            row["collection"] or "",
            row["journal"] or "",
            row["year"] or "",
        ),
    )
