import json

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from article import choices
from article.models import Article


@login_required
def data_availability_chart(request):
    """
    View that renders a chart showing the evolution (by year) of articles
    regarding their data availability status.
    """
    status_labels = dict(choices.DATA_AVAILABILITY_STATUS)

    qs = (
        Article.objects.filter(
            pub_date_year__isnull=False,
        )
        .exclude(pub_date_year="")
        .values("pub_date_year", "data_availability_status")
        .annotate(count=Count("id"))
        .order_by("pub_date_year")
    )

    years_set = set()
    data_map = {}

    for row in qs:
        year = row["pub_date_year"]
        status = row["data_availability_status"] or choices.DATA_AVAILABILITY_STATUS_NOT_PROCESSED
        count = row["count"]
        years_set.add(year)

        if status not in data_map:
            data_map[status] = {}
        data_map[status][year] = count

    years = sorted(years_set)

    series = []
    for status_value, status_label in choices.DATA_AVAILABILITY_STATUS:
        if status_value in data_map:
            series.append(
                {
                    "name": str(status_label),
                    "type": "bar",
                    "stack": "total",
                    "emphasis": {"focus": "series"},
                    "data": [data_map[status_value].get(y, 0) for y in years],
                }
            )

    context = {
        "years_json": json.dumps(years),
        "series_json": json.dumps(series, ensure_ascii=False),
    }

    return render(request, "article/data_availability_chart.html", context)
