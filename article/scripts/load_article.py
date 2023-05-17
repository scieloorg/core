from article.tasks import load_articles
from packtools.sps.utils import xml_utils

from django.contrib.auth import get_user_model

User = get_user_model()

def run(user_id=None, file_path=None):
    # Xml usado para testes.
    file_path = file_path or "article/fixtures/0034-7094-rba-69-03-0227.xml"

    load_articles.apply_async(args=(user_id, file_path))
