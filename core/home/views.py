from django.shortcuts import render
import feedparser
from django.views.decorators.http import require_GET

BLOG_URL_RSS = "https://blog.scielo.org/feed/"

YOUTUBE_URL_SCIELO = "https://www.youtube.com/feeds/videos.xml?channel_id=UCE5uQwLX5wkkJvtnjOFK-Hw"

from django.http import JsonResponse


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
        if 'media_content' in entry and entry.media_content:
            post["image"] = entry.media_content[0].get("url")
        elif 'media_thumbnail' in entry and entry.media_thumbnail:
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

