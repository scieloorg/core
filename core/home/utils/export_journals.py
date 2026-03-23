import csv
import logging

import xlwt
from django.http import HttpResponse
from django.utils import timezone

from journal.models import SciELOJournal

logger = logging.getLogger(__name__)

HEADERS = ["journals", "scielo_url", "publisher"]


def get_scielo_journals_data(filters=None):
    try:
        qs = SciELOJournal.objects.all()
        if filters is not None:
            qs = qs.filter(filters)
        scielo_journals = qs.values(
            "journal__title",
            "collection__domain",
            "journal__owner_history__institution__institution__institution_identification__name",
            "issn_scielo",
        )

        formatted_data = []
        for journal in scielo_journals:
            title = journal.get("journal__title", "")
            issn_scielo = journal.get("issn_scielo", "")
            domain = journal.get("collection__domain", "")
            owner = journal.get(
                "journal__owner_history__institution__institution__institution_identification__name",
                "",
            )
            scielo_url = (
                f"{domain.rstrip('/')}/scielo.php?script=sci_serial&pid={issn_scielo}&lng=en"
            )
            formatted_data.append(
                {
                    "title": title,
                    "scielo_url": scielo_url,
                    "owner": owner,
                }
            )
        return formatted_data
    except Exception as e:
        logger.error(f"Error fetching scielo journals data: {e}")
        return []


def generate_csv_response(journals_data):
    date = timezone.now().strftime("%Y-%m-%d")
    filename = f"journals_{date}.csv"
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    try:
        writer = csv.writer(response)
        writer.writerow(HEADERS)
        for journal in journals_data:
            writer.writerow(
                [journal.get("title"), journal.get("scielo_url"), journal.get("owner")]
            )
        logger.info(f"Generated CSV file with: {len(journals_data)} journals")
    except Exception as e:
        logger.error(f"Error generating CSV file: {e}")
        response = HttpResponse("Error generating CSV file", status=500)
    return response


def generate_xls_response(journals_data):
    date = timezone.now().strftime("%Y-%m-%d")
    filename = f"journals_{date}.xls"
    response = HttpResponse(content_type="application/vnd.ms-excel")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    try:
        wb = xlwt.Workbook(encoding="utf-8")
        ws = wb.add_sheet("journals")
        for col, header in enumerate(HEADERS):
            ws.write(0, col, header)
        for row, journal in enumerate(journals_data, start=1):
            ws.write(row, 0, journal.get("title"))
            ws.write(row, 1, journal.get("scielo_url"))
            ws.write(row, 2, journal.get("owner"))
        wb.save(response)
        logger.info(f"Generated XLS file with: {len(journals_data)} journals")
    except Exception as e:
        logger.error(f"Error generating XLS file: {e}")
        response = HttpResponse("Error generating XLS file", status=500)
    return response
