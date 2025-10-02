import os
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.timezone import make_aware
from freezegun import freeze_time

from article import choices
from article.models import Article, ArticleFormat
from article.tasks import (
    get_researcher_identifier_unnormalized,
    migrate_path_xml_pid_provider_to_pid_provider,
    normalize_stored_email,
    remove_duplicate_articles,
)
from researcher.models import ResearcherIdentifier

User = get_user_model()


class RemoveDuplicateArticlesTest(TestCase):
    def create_article_at_time(self, dt, v3):
        @freeze_time(dt)
        def create_article():
            Article.objects.create(
                pid_v3=v3, created=make_aware(datetime.strptime(dt, "%Y-%m-%d"))
            )

        create_article()

    def test_remove_duplicates_keeps_earliest_article(self):
        self.create_article_at_time("2023-01-01", "pid1")
        self.create_article_at_time("2023-01-02", "pid1")
        self.create_article_at_time("2023-01-03", "pid1")
        remove_duplicate_articles()
        self.assertEqual(Article.objects.all().count(), 1)
        self.assertEqual(
            Article.objects.all()[0].created, make_aware(datetime(2023, 1, 1))
        )

    def test_no_removal_if_only_one_article(self):
        self.create_article_at_time("2023-01-01", "pid1")
        remove_duplicate_articles()
        self.assertEqual(Article.objects.all().count(), 1)
        self.assertEqual(
            Article.objects.all()[0].created, make_aware(datetime(2023, 1, 1))
        )

    def test_remove_duplicates_for_multiple_pids(self):
        self.create_article_at_time("2022-06-03", "pid2")
        self.create_article_at_time("2022-06-04", "pid2")
        self.create_article_at_time("2022-07-08", "pid3")
        self.create_article_at_time("2022-06-14", "pid3")
        remove_duplicate_articles()
        self.assertEqual(Article.objects.filter(pid_v3="pid2").count(), 1)
        self.assertEqual(Article.objects.filter(pid_v3="pid3").count(), 1)
        self.assertEqual(
            Article.objects.get(pid_v3="pid2").created, make_aware(datetime(2022, 6, 3))
        )
        self.assertEqual(
            Article.objects.get(pid_v3="pid3").created,
            make_aware(datetime(2022, 6, 14)),
        )


class NormalizeEmailResearcherIdentifierTest(TestCase):
    def setUp(self):
        self.emails = [
            '<a href="mailto:jgarrido@ucv.cl">jgarrido@ucv.cl</a>',
            '<a href="mailto:gagopa39@hotmail.com">gagopa39@hotmail.com</a>',
            " herbet@ufs.br",
            "pilosaperez@gmail.com.",
            "cortes- camarillo@hotmail.com",
            "ulrikekeyser@upn162-zamora.edu.mx",
            "cortescamarillo@hotmail.com",
            "candelariasgro@yahoo.com",
            'mailto:user@hotmail.com">gagopa39@hotmail.com</a>',
        ]

        self.orcids = [
            "0000-0002-9147-0547",
            "0000-0003-3622-3428",
            "0000-0002-4842-3331",
            "0000-0003-1314-4073",
        ]
        ResearcherIdentifier.objects.bulk_create(
            [
                ResearcherIdentifier(identifier=email, source_name="EMAIL")
                for email in self.emails
            ]
        )
        ResearcherIdentifier.objects.bulk_create(
            [
                ResearcherIdentifier(identifier=orcid, source_name="ORCID")
                for orcid in self.orcids
            ]
        )

    def test_normalize_stored_email(self):
        unnormalized_identifiers = get_researcher_identifier_unnormalized()
        self.assertEqual(6, unnormalized_identifiers.count())

        normalize_stored_email()

        normalized_emails = [
            "jgarrido@ucv.cl",
            "gagopa39@hotmail.com",
            "herbet@ufs.br",
            "pilosaperez@gmail.com",
            "cortes-camarillo@hotmail.com",
            "user@hotmail.com",
        ]

        for email in normalized_emails:
            with self.subTest(email=email):
                self.assertTrue(
                    ResearcherIdentifier.objects.filter(identifier=email).exists(),
                    f"E-mail '{email}' unnormalized",
                )


class PubMedArticleTypeFilteringTest(TestCase):
    """Test that PubMed format generation only happens for eligible article types"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")

    @patch("article.models.ArticleFormat.generate")
    def test_pubmed_format_generated_for_research_article(self, mock_generate):
        """Test that PubMed format is generated for research-article type"""
        article = Article.objects.create(
            pid_v3="test-pid-1",
            article_type="research-article",
            sps_pkg_name="test-pkg-1",
        )

        ArticleFormat.generate_formats(self.user, article)

        # Check that generate was called for pubmed
        pubmed_calls = [
            call for call in mock_generate.call_args_list if call[0][2] == "pubmed"
        ]
        self.assertEqual(len(pubmed_calls), 1, "PubMed format should be generated")

    @patch("article.models.ArticleFormat.generate")
    def test_pubmed_format_not_generated_for_ineligible_type(self, mock_generate):
        """Test that PubMed format is NOT generated for ineligible article types"""
        article = Article.objects.create(
            pid_v3="test-pid-2",
            article_type="book-review",  # Not in PUBMED_ARTICLE_TYPES
            sps_pkg_name="test-pkg-2",
        )

        ArticleFormat.generate_formats(self.user, article)

        # Check that generate was NOT called for pubmed
        pubmed_calls = [
            call for call in mock_generate.call_args_list if call[0][2] == "pubmed"
        ]
        self.assertEqual(
            len(pubmed_calls), 0, "PubMed format should NOT be generated"
        )

    @patch("article.models.ArticleFormat.generate")
    def test_pmc_format_always_generated(self, mock_generate):
        """Test that PMC format is always generated regardless of article type"""
        # Test with ineligible type for PubMed
        article = Article.objects.create(
            pid_v3="test-pid-3",
            article_type="book-review",
            sps_pkg_name="test-pkg-3",
        )

        ArticleFormat.generate_formats(self.user, article)

        # Check that generate was called for pmc
        pmc_calls = [call for call in mock_generate.call_args_list if call[0][2] == "pmc"]
        self.assertEqual(len(pmc_calls), 1, "PMC format should always be generated")

    @patch("article.models.ArticleFormat.generate")
    def test_pubmed_format_for_various_eligible_types(self, mock_generate):
        """Test that PubMed format is generated for various eligible article types"""
        eligible_types = [
            "research-article",
            "review-article",
            "case-report",
            "editorial",
            "letter",
        ]

        for i, article_type in enumerate(eligible_types):
            with self.subTest(article_type=article_type):
                mock_generate.reset_mock()
                article = Article.objects.create(
                    pid_v3=f"test-pid-eligible-{i}",
                    article_type=article_type,
                    sps_pkg_name=f"test-pkg-eligible-{i}",
                )

                ArticleFormat.generate_formats(self.user, article)

                pubmed_calls = [
                    call
                    for call in mock_generate.call_args_list
                    if call[0][2] == "pubmed"
                ]
                self.assertEqual(
                    len(pubmed_calls),
                    1,
                    f"PubMed format should be generated for {article_type}",
                )
