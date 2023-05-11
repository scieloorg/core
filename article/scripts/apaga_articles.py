from article.models import Article, DOI, Language, Researcher, Issue, TocSection, License, Keyword
from vocabulary.models import Vocabulary
def run():
    Article.objects.all().delete()
    DOI.objects.all().delete()
    Language.objects.all().delete()
    Researcher.objects.all().delete()
    Issue.objects.all().delete()
    License.objects.all().delete()
    TocSection.objects.all().delete()
    Keyword.objects.all().delete()
    Vocabulary.objects.all().delete()