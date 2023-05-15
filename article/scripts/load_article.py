from article.tasks import load_articles
from packtools.sps.utils import xml_utils

from django.contrib.auth import get_user_model

User = get_user_model()

def run(user=None):
    # Xml usado para testes.
    xmltree = xml_utils.get_xml_tree("article/fixtures/0034-8910-rsp-48-2-0249.xml")
    user = user or User.objects.first()                        
    # kombu.exceptions.EncodeError: Object of type is not JSON serializable
    # load_articles.apply_async(args=(user, xmltree))

    load_articles(user=user, xmltree=xmltree)