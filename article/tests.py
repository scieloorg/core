import os
import tempfile
import pytest


from freezegun import freeze_time
from django.test import TestCase
from datetime import datetime
from django.utils.timezone import make_aware
from unittest.mock import patch, MagicMock

from article.models import Article
from article.tasks import remove_duplicate_articles, normalize_stored_email, get_researcher_identifier_unnormalized, migrate_path_xml_pid_provider_to_pid_provider
from researcher.models import ResearcherIdentifier
from django.contrib.auth import get_user_model

User = get_user_model()



class RemoveDuplicateArticlesTest(TestCase):
    def create_article_at_time(self, dt, v3):
        @freeze_time(dt)
        def create_article():
            Article.objects.create(pid_v3=v3, created=make_aware(datetime.strptime(dt, "%Y-%m-%d")))
        create_article()

    def test_remove_duplicates_keeps_earliest_article(self):
        self.create_article_at_time("2023-01-01", "pid1")
        self.create_article_at_time("2023-01-02", "pid1")
        self.create_article_at_time("2023-01-03", "pid1")
        remove_duplicate_articles()
        self.assertEqual(Article.objects.all().count(), 1)
        self.assertEqual(Article.objects.all()[0].created, make_aware(datetime(2023, 1, 1)))

    def test_no_removal_if_only_one_article(self):
        self.create_article_at_time("2023-01-01", "pid1")
        remove_duplicate_articles()
        self.assertEqual(Article.objects.all().count(), 1)
        self.assertEqual(Article.objects.all()[0].created, make_aware(datetime(2023, 1, 1)))

    def test_remove_duplicates_for_multiple_pids(self):
        self.create_article_at_time("2022-06-03", "pid2")
        self.create_article_at_time("2022-06-04", "pid2")
        self.create_article_at_time("2022-07-08", "pid3")
        self.create_article_at_time("2022-06-14", "pid3")
        remove_duplicate_articles()
        self.assertEqual(Article.objects.filter(pid_v3="pid2").count(), 1)
        self.assertEqual(Article.objects.filter(pid_v3="pid3").count(), 1)
        self.assertEqual(Article.objects.get(pid_v3="pid2").created, make_aware(datetime(2022, 6, 3)))
        self.assertEqual(Article.objects.get(pid_v3="pid3").created, make_aware(datetime(2022, 6, 14)))


class NormalizeEmailResearcherIdentifierTest(TestCase):
    def setUp(self):
        self.emails = [
            '<a href="mailto:jgarrido@ucv.cl">jgarrido@ucv.cl</a>',
            '<a href="mailto:gagopa39@hotmail.com">gagopa39@hotmail.com</a>',
            ' herbet@ufs.br',
            'pilosaperez@gmail.com.',
            'cortes- camarillo@hotmail.com',
            'ulrikekeyser@upn162-zamora.edu.mx',
            'cortescamarillo@hotmail.com',
            'candelariasgro@yahoo.com',
            'mailto:user@hotmail.com">gagopa39@hotmail.com</a>',
        ]

        self.orcids = [
            '0000-0002-9147-0547',
            '0000-0003-3622-3428',
            '0000-0002-4842-3331',
            '0000-0003-1314-4073',
        ]
        ResearcherIdentifier.objects.bulk_create([ResearcherIdentifier(identifier=email, source_name="EMAIL") for email in self.emails])
        ResearcherIdentifier.objects.bulk_create([ResearcherIdentifier(identifier=orcid, source_name="ORCID") for orcid in self.orcids])

    def test_normalize_stored_email(self):
        unnormalized_identifiers = get_researcher_identifier_unnormalized()
        self.assertEqual(6, unnormalized_identifiers.count())

        normalize_stored_email()

        normalized_emails = [
            'jgarrido@ucv.cl',
            'gagopa39@hotmail.com',
            'herbet@ufs.br',
            'pilosaperez@gmail.com',
            'cortes-camarillo@hotmail.com',
            'user@hotmail.com',
        ]

        for email in normalized_emails:
            with self.subTest(email=email):
                self.assertTrue(
                    ResearcherIdentifier.objects.filter(identifier=email).exists(),
                    f"E-mail '{email}' unnormalized"
                )
