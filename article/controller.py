import csv

from .models import Article, ArticleFunding
from institution.models import Sponsor


def load_financial_data(row, user):
    sponsor = Sponsor.get_or_create(
        inst_name=row.get('funding_source'),
        inst_acronym=None,
        level_1=None,
        level_2=None,
        level_3=None,
        location=None,
        official=None,
        is_official=None
    )
    article_funding = ArticleFunding.get_or_create(award_id=row.get('award_id'), funding_source=sponsor)
    article = Article.get_or_create(pid_v2=row.get('pid_v2'), funding=article_funding)

    return article


def read_file(user):
    with open("article/fixtures/financial_data.csv", 'r') as csvfile:
        data = csv.DictReader(csvfile)
        for row in data:
            load_financial_data(row, user)
