import csv
import logging

import feedparser
import xlwt
from django.db.models import Prefetch, Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.translation import get_language
from django.views.decorators.http import require_GET
from journal.models import OwnerHistory, SciELOJournal

from core.home.models import default_journal_filter, slugs_to_category_code

logger = logging.getLogger(__name__)

BLOG_URL_RSS = "https://blog.scielo.org/"

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
    lang_code = get_language()
    lang_code = "" if lang_code == "pt-br" else lang_code
    if not lang_code:
        url = BLOG_URL_RSS + "/feed/"
    else:
        url = BLOG_URL_RSS + lang_code + "/feed/"
    posts = get_rss_feed_json(url)
    return JsonResponse({"posts": posts})


@require_GET
def youtube_feed_json(request):
    posts = get_rss_feed_json(YOUTUBE_URL_SCIELO)
    return JsonResponse({"posts": posts})


def _get_scielo_journals_data(request=None):
    search_term = ""
    starts_with_letter = ""
    active_or_discontinued = ""
    category = None
    if request is not None:
        search_term = request.GET.get("search_term", "")
        starts_with_letter = request.GET.get("start_with_letter", "")
        active_or_discontinued = list(request.GET.get("tab", ""))
        category = request.GET.get("category")

    filters = default_journal_filter(
        search_term, starts_with_letter, active_or_discontinued
    )
    if category:
        category_code = slugs_to_category_code.get(category)
        if category_code:
            filters &= Q(journal__subject__code=category_code)

    scielo_journals = (
        SciELOJournal.objects.filter(filters)
        .select_related("journal", "collection")
        .prefetch_related(
            Prefetch(
                "journal__owner_history",
                queryset=OwnerHistory.objects.select_related(
                    "organization",
                    "institution__institution__institution_identification",
                ).order_by("sort_order"),
            )
        )
        .order_by("journal__title")
        .distinct()
    )

    return [scielo_journal.as_export_dict() for scielo_journal in scielo_journals]


def _journals_download_filename(request, extension):
    date = timezone.now().strftime("%Y-%m-%d")
    category = request.GET.get("category") if request is not None else None
    if category and slugs_to_category_code.get(category):
        prefix = f"{category.replace('-', '_')}_journals"
    else:
        prefix = "all_journals"
    return f"{prefix}_{date}.{extension}"


def _cell_value(value):
    return "" if value is None else str(value)


def download_xls_journals_page_scielo_org(request):
    filename = _journals_download_filename(request, "xls")

    response = HttpResponse(content_type="application/vnd.ms-excel")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    try:
        wb = xlwt.Workbook(encoding="utf-8")
        ws = wb.add_sheet("journals")
        headers = ["journals", "scielo_url", "publisher"]

        for col, header in enumerate(headers):
            ws.write(0, col, header)

        journals_data = _get_scielo_journals_data(request)
        for row, journal in enumerate(journals_data, start=1):
            ws.write(row, 0, _cell_value(journal.get("title")))
            ws.write(row, 1, _cell_value(journal.get("scielo_url")))
            ws.write(row, 2, _cell_value(journal.get("owner")))
        wb.save(response)
        logger.info(f"Generated XLS file with: {len(journals_data)} journals")
    except Exception as e:
        logger.error(f"Error generating XLS file: {e}")
        response = HttpResponse("Error generating file", status=500)
    return response


def download_csv_journals_page_scielo_org(request):
    filename = _journals_download_filename(request, "csv")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    try:
        writer = csv.writer(response)
        headers = ["journals", "scielo_url", "publisher"]
        writer.writerow(headers)
        journals_data = _get_scielo_journals_data(request)
        for journal in journals_data:
            writer.writerow(
                [
                    _cell_value(journal.get("title")),
                    _cell_value(journal.get("scielo_url")),
                    _cell_value(journal.get("owner")),
                ]
            )
        logger.info(f"Generated CSV file with: {len(journals_data)} journals")
    except Exception as e:
        logger.error(f"Error generating CSV file: {e}")
        response = HttpResponse("Error generating file", status=500)

    return response
