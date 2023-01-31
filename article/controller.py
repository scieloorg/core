import csv
import logging

from .models import Article, ArticleFunding
from institution.models import Sponsor


def load_financial_data(row, user):
    article_findings = []
    for institution in row.get('funding_source').split(','):
        sponsor = Sponsor.get_or_create(
            inst_name=institution,
            inst_acronym=None,
            level_1=None,
            level_2=None,
            level_3=None,
            location=None,
            official=None,
            is_official=None
        )
        article_findings.append(ArticleFunding.get_or_create(award_id=row.get('award_id'), funding_source=sponsor, user=user))
    article = Article.get_or_create(pid_v2=row.get('pid_v2'), fundings=article_findings, user=user)

    return article


def read_file(user, file_path):
    with open(file_path, 'r') as csvfile:
        data = csv.DictReader(csvfile)
        for row in data:
            logging.debug(row)
            load_financial_data(row, user)
