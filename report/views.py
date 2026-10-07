import csv

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page

from report import data_availability
from report.forms import DataAvailabilityFilterForm, VisualElementTotalsFilterForm
from report.visual_element_totals import (
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
            "header_title": _("Figure, Table and Equation Counts"),
            "page_title": _("Figure, Table and Equation Counts"),
            "header_icon": "table",
        },
    )


def visual_element_totals_csv_view(request):
    form = VisualElementTotalsFilterForm(request.GET)
    filters = _filters_from_form(form)
    if filters is None:
        return visual_element_totals_view(request)

    article_ids = filtered_article_ids(**filters)
    columns, rows = spreadsheet_rows(article_ids, collection=filters["collection"])

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="visual_element_totals.csv"'
    )
    writer = csv.writer(response, delimiter=";")
    writer.writerow(columns)
    for row in rows:
        writer.writerow(
            [
                "" if row.get(column) is None else row.get(column)
                for column in columns
            ]
        )
    return response


# Relatórios públicos listados em /report/.
# Para adicionar um relatório: inclua o path em report/urls.py e uma entrada aqui.
PUBLIC_REPORTS = [
    {
        "url_name": "report_data_availability",
        "title": _("Data availability"),
        "description": _(
            "Articles by data availability status per year, with totals and "
            "percentages. Filters: collection, journal and online publication year."
        ),
    },
]


def report_index_view(request):
    return render(request, "report/index.html", {"reports": PUBLIC_REPORTS})


# relatório público consulta toda a tabela Article; evita recalcular a cada acesso
DATA_AVAILABILITY_CACHE_SECONDS = 60 * 60


@cache_page(DATA_AVAILABILITY_CACHE_SECONDS)
def data_availability_view(request):
    """
    Relatório público: Article.data_availability_status por ano,
    com total e porcentagem, filtrável por coleção, periódico e
    ano de publicação online.
    """
    form = DataAvailabilityFilterForm(request.GET)
    filters = form.filters()
    queryset = data_availability.filter_articles(
        collection=filters["collection"],
        journal=filters["journal"],
        year_from=filters["year_from"],
        year_to=filters["year_to"],
    )
    report = data_availability.build_report(queryset, group_by=filters["group_by"])

    if request.GET.get("format") == "csv":
        return _data_availability_csv(report)

    query = request.GET.copy()
    query.pop("format", None)
    return render(
        request,
        "report/data_availability.html",
        {
            "form": form,
            "filters": filters,
            "report": report,
            "journals": data_availability.journals_for(filters["collection"]),
            "years": data_availability.pub_years_for(
                filters["collection"], filters["journal"]
            ),
            "query_string": query.urlencode(),
        },
    )


@cache_page(DATA_AVAILABILITY_CACHE_SECONDS)
def data_availability_options_view(request):
    """Opções dos filtros dependentes (JSON): periódicos e anos disponíveis."""
    filters = DataAvailabilityFilterForm(request.GET).filters()
    return JsonResponse(
        data_availability.filter_options(filters["collection"], filters["journal"])
    )


def _data_availability_csv(report):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        'attachment; filename="data_availability.csv"'
    )
    writer = csv.writer(response, delimiter=";")
    header = ["year", "total"]
    for status, _label in report["columns"]:
        header.extend([status, f"{status} (%)"])
    writer.writerow(header)
    for row in report["rows"] + [dict(report["totals"], year="total")]:
        line = [row["year"] or "", row["total"]]
        for cell in row["cells"]:
            line.extend([cell["count"], cell["percent"]])
        writer.writerow(line)
    return response
