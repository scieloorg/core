import csv
import logging

import feedparser
import xlwt
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from journal.models import SciELOJournal

logger = logging.getLogger(__name__)

BLOG_URL_RSS = "https://blog.scielo.org/feed/"

YOUTUBE_URL_SCIELO = (
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCE5uQwLX5wkkJvtnjOFK-Hw"
)


def get_rss_feed_json(url):
    rss_content = feedparser.parse(url)
    posts = []
    for entry in rss_content.entries:
        post = {
            "title": entry.title,
            "link": entry.link,
            "description": entry.description,
            "date": entry.published,
            "image": None,
        }
        if "media_content" in entry and entry.media_content:
            post["image"] = entry.media_content[0].get("url")
        elif "media_thumbnail" in entry and entry.media_thumbnail:
            post["image"] = entry.media_thumbnail[0].get("url")
        posts.append(post)
    return posts


@require_GET
def blog_feed_json(request):
    posts = get_rss_feed_json(BLOG_URL_RSS)
    return JsonResponse({"posts": posts})


@require_GET
def youtube_feed_json(request):
    posts = get_rss_feed_json(YOUTUBE_URL_SCIELO)
    return JsonResponse({"posts": posts})


def _get_scielo_journals_data():
    try:
        scielo_journals = SciELOJournal.objects.values(
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
                f"http://{domain}/scielo.php?script=sci_serial&pid={issn_scielo}&lng=en"
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


def download_xls_journals_page_scielo_org(request):
    date = timezone.now().strftime("%Y-%m-%d")
    filename = f"journals_{date}.xls"

    response = HttpResponse(content_type="application/vnd.ms-excel")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    try:
        wb = xlwt.Workbook(encoding="utf-8")
        ws = wb.add_sheet("journals")
        headers = ["journals", "scielo_url", "publisher"]

        for col, header in enumerate(headers):
            ws.write(0, col, header)

        journals_data = _get_scielo_journals_data()
        for row, journal in enumerate(journals_data, start=1):
            ws.write(row, 0, journal.get("title"))
            ws.write(row, 1, journal.get("scielo_url"))
            ws.write(row, 2, journal.get("owner"))
        wb.save(response)
        logger.info(f"Generated XLS file with: {len(journals_data)} journals")
    except Exception as e:
        logger.error(f"Error generating XLS file: {e}")
        response = HttpResponse("Error generating file", status=500)
    return response


def download_csv_journals_page_scielo_org(request):
    date = timezone.now().strftime("%Y-%m-%d")
    filename = f"journals_{date}.csv"
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    try:
        writer = csv.writer(response)
        headers = ["journals", "scielo_url", "publisher"]
        writer.writerow(headers)
        journals_data = _get_scielo_journals_data()
        for journal in journals_data:
            writer.writerow(
                [journal.get("title"), journal.get("scielo_url"), journal.get("owner")]
            )
        logger.info(f"Generated CSV file with: {len(journals_data)} journals")
    except Exception as e:
        logger.error(f"Error generating CSV file: {e}")
        response = HttpResponse("Error generating file", status=500)

    return response
