import logging

import feedparser
from django.http import HttpResponse, JsonResponse
from django.utils.translation import get_language
from django.views.decorators.http import require_GET

from core.home.utils.export_journals import (
    generate_csv_response,
    generate_xls_response,
    get_scielo_journals_data,
)

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


def download_xls_journals_page_scielo_org(request):
    journals_data = get_scielo_journals_data()
    return generate_xls_response(journals_data)


def download_csv_journals_page_scielo_org(request):
    journals_data = get_scielo_journals_data()
    return generate_csv_response(journals_data)
