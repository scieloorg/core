import csv

from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from report.forms import VisualElementTotalsFilterForm
from report.visual_element_totals import (
    SPREADSHEET_COLUMNS,
    filtered_article_ids,
    spreadsheet_rows,
    yearly_totals,
)


def _filters_from_form(form):
    if not form.is_valid():
        return None
    return {
        "collection": form.cleaned_data.get("collection"),
        "thematic_area": form.cleaned_data.get("thematic_area"),
        "journal": form.cleaned_data.get("journal"),
        "pid": form.cleaned_data.get("pid"),
    }


def visual_element_totals_view(request):
    form = VisualElementTotalsFilterForm(request.GET)
    yearly_rows = []
    filters = _filters_from_form(form)
    selected_filters = []
    if filters is not None:
        article_ids = filtered_article_ids(**filters)
        yearly_rows = yearly_totals(article_ids)
        for name in ("collection", "thematic_area", "journal", "pid"):
            value = filters.get(name)
            if value:
                selected_filters.append((form.fields[name].label, value))
    return render(
        request,
        "report/visual_element_totals.html",
        {
            "form": form,
            "yearly_rows": yearly_rows,
            "selected_filters": selected_filters,
            "header_title": _("Visual elements totals"),
            "page_title": _("Visual elements totals"),
            "header_icon": "table",
        },
    )


def visual_element_totals_csv_view(request):
    form = VisualElementTotalsFilterForm(request.GET)
    filters = _filters_from_form(form)
    if filters is None:
        return visual_element_totals_view(request)

    article_ids = filtered_article_ids(**filters)
    rows = spreadsheet_rows(article_ids, collection=filters["collection"])

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="visual_element_totals.csv"'
    )
    writer = csv.writer(response, delimiter=";")
    writer.writerow(SPREADSHEET_COLUMNS)
    for row in rows:
        writer.writerow(
            [
                "" if row.get(column) is None else row.get(column)
                for column in SPREADSHEET_COLUMNS
            ]
        )
    return response
