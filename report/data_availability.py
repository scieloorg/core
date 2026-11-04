from django.db.models import Count, Exists, OuterRef
from django.utils.translation import gettext_lazy as _

from article import choices
from article.models import Article
from journal.models import Journal, SciELOJournal

GROUP_BY_ISSUE_YEAR = "issue_year"
GROUP_BY_PUB_YEAR = "pub_year"

GROUP_BY_OPTIONS = (
    (GROUP_BY_ISSUE_YEAR, _("Issue year (bibliographic strip)")),
    (GROUP_BY_PUB_YEAR, _("Online publication year")),
)

GROUP_BY_FIELDS = {
    GROUP_BY_ISSUE_YEAR: "issue__year",
    GROUP_BY_PUB_YEAR: "pub_date_year",
}


def status_columns():
    return list(choices.DATA_AVAILABILITY_STATUS)


def filter_articles(collection=None, journal=None, year_from=None, year_to=None):
    """
    Artigos considerados no relatório.

    year_from / year_to referem-se ao ano de publicação online (pub_date_year),
    independente do ano do fascículo.
    """
    qs = Article.objects.exclude(data_status__in=choices.DATA_STATUS_EXCLUSION_LIST)
    if collection:
        # Exists evita contagem duplicada de periódicos em mais de uma coleção
        qs = qs.filter(
            Exists(
                SciELOJournal.objects.filter(
                    journal_id=OuterRef("journal_id"),
                    collection=collection,
                )
            )
        )
    if journal:
        qs = qs.filter(journal=journal)
    if year_from:
        qs = qs.filter(pub_date_year__gte=year_from)
    if year_to:
        qs = qs.filter(pub_date_year__lte=year_to)
    return qs


def journals_for(collection=None):
    journals = Journal.objects.all()
    if collection:
        journals = journals.filter(
            Exists(
                SciELOJournal.objects.filter(
                    journal_id=OuterRef("pk"),
                    collection=collection,
                )
            )
        )
    return journals.order_by("title")


def pub_years_for(collection=None, journal=None):
    """Anos de publicação online disponíveis, em ordem decrescente."""
    return list(
        filter_articles(collection=collection, journal=journal)
        .filter(pub_date_year__regex=r"^\d{4}$")
        .order_by("-pub_date_year")
        .values_list("pub_date_year", flat=True)
        .distinct()
    )


def filter_options(collection=None, journal=None):
    """Opções dependentes: coleção -> periódicos; coleção + periódico -> anos."""
    return {
        "journals": [
            {"id": item.pk, "label": str(item)} for item in journals_for(collection)
        ],
        "years": pub_years_for(collection, journal),
    }


def percent(value, total):
    return round(value * 100 / total, 2) if total else 0


def _make_row(year, counts, columns):
    total = sum(counts.values())
    return {
        "year": year,
        "total": total,
        "cells": [
            {
                "status": status,
                "count": counts.get(status, 0),
                "percent": percent(counts.get(status, 0), total),
            }
            for status, _label in columns
        ],
    }


def build_report(queryset, group_by=GROUP_BY_ISSUE_YEAR):
    """
    Contabiliza Article.data_availability_status por ano.

    Retorna dict com:
        columns: [(status, label), ...]
        rows: [{"year", "total", "cells": [{"status", "count", "percent"}]}]
        totals: {"year": None, "total", "cells": [...]}
    """
    year_field = GROUP_BY_FIELDS.get(group_by, GROUP_BY_FIELDS[GROUP_BY_ISSUE_YEAR])
    data = (
        queryset.order_by()
        .values(year_field, "data_availability_status")
        .annotate(n=Count("pk"))
    )

    columns = status_columns()
    by_year = {}
    for item in data:
        year = item[year_field] or None
        status = (
            item["data_availability_status"]
            or choices.DATA_AVAILABILITY_STATUS_NOT_PROCESSED
        )
        counts = by_year.setdefault(year, {})
        counts[status] = counts.get(status, 0) + item["n"]

    # anos em ordem decrescente; sem ano por último
    years = sorted((year for year in by_year if year), reverse=True)
    if None in by_year:
        years.append(None)
    rows = [_make_row(year, by_year[year], columns) for year in years]

    all_counts = {}
    for counts in by_year.values():
        for status, n in counts.items():
            all_counts[status] = all_counts.get(status, 0) + n

    return {
        "columns": columns,
        "rows": rows,
        "totals": _make_row(None, all_counts, columns),
    }
