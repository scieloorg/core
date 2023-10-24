import pandas as pd
from io import BytesIO
from datetime import datetime

from journal.models import Journal
from django.http import HttpResponse


def download_csv(request):
    """
    This function return a csv file with the Journal data
    """
    # TODO
    # Inserir status (current, deceased ou suspended)
    # Depende da nova modelagem de Event
    items = (
        Journal.objects.all()
        .order_by("title")
        .values("title", "collection__domain", "publisher", "official__issnl")
    )

    def modify_domain(domain, issnl):
        if domain and issnl:
            return f"http://{domain}/scielo.php?script=sci_serial&pid={issnl}&lng=en"

    items = [
        {
            "title": item["title"],
            "collection__domain": modify_domain(
                item["collection__domain"], item["official__issnl"]
            ),
            "publisher": item["publisher"],
        }
        for item in items
    ]

    df = pd.DataFrame(items)
    df.rename(
        columns={
            "title": "journals",
            "collection__domain": "scielo_url",
            "publisher": "publisher",
        },
        inplace=True,
    )

    df.fillna("", inplace=True)
    df.replace(False, "No", inplace=True)
    df.replace(True, "Yes", inplace=True)

    filename = f"journals-{datetime.now().strftime('%a-%d-%b-%Y-%H_%M_%S')}.csv"

    with BytesIO() as b:
        df.to_csv(b, index=False)
        content_type = "text/csv"
        response = HttpResponse(b.getvalue(), content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response