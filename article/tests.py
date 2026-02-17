import os
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.timezone import make_aware
from freezegun import freeze_time

from article.models import Article
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


class ArticleAffiliationTest(TestCase):
    """Tests for ArticleAffiliation model."""
    
    def setUp(self):
        """Set up test data."""
        from article.models import ArticleAffiliation
        from location.models import Country, Location
        from organization.models import Organization
        
        self.user = User.objects.create_user(username="testuser", password="testpass")
        
        # Create a location
        self.country = Country.objects.create(
            name="Brazil",
            acron2="BR",
            acron3="BRA"
        )
        self.location = Location.objects.create(
            country=self.country,
            state_name="São Paulo",
            state_acronym="SP",
            city_name="São Paulo"
        )
        
        # Create an organization
        self.organization = Organization.objects.create(
            name="Universidade de São Paulo",
            acronym="USP",
            location=self.location,
            creator=self.user
        )
        
        # Create an article
        self.article = Article.objects.create(creator=self.user)
        
        self.ArticleAffiliation = ArticleAffiliation
    
    def test_article_affiliation_create_with_organization(self):
        """Test creating ArticleAffiliation with organization."""
        affiliation = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization
        )
        
        self.assertIsNotNone(affiliation.id)
        self.assertEqual(affiliation.article, self.article)
        self.assertEqual(affiliation.organization, self.organization)
        self.assertEqual(affiliation.creator, self.user)
    
    def test_article_affiliation_create_with_raw_data(self):
        """Test creating ArticleAffiliation with raw data."""
        affiliation = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            raw_text="Test University",
            raw_institution_name="Test University",
            raw_country_name="Brazil",
            raw_country_code="BR"
        )
        
        self.assertIsNotNone(affiliation.id)
        self.assertEqual(affiliation.raw_text, "Test University")
        self.assertEqual(affiliation.raw_institution_name, "Test University")
        self.assertEqual(affiliation.raw_country_name, "Brazil")
        self.assertEqual(affiliation.raw_country_code, "BR")
    
    def test_article_affiliation_get(self):
        """Test getting an ArticleAffiliation."""
        affiliation = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization
        )
        
        retrieved = self.ArticleAffiliation.get(
            article=self.article,
            organization=self.organization
        )
        
        self.assertEqual(retrieved.id, affiliation.id)
    
    def test_article_affiliation_create_or_update_creates(self):
        """Test create_or_update creates new affiliation."""
        affiliation = self.ArticleAffiliation.create_or_update(
            user=self.user,
            article=self.article,
            organization=self.organization,
            raw_text="Initial"
        )
        
        self.assertIsNotNone(affiliation.id)
        self.assertEqual(self.ArticleAffiliation.objects.count(), 1)
    
    def test_article_affiliation_create_or_update_updates(self):
        """Test create_or_update updates existing affiliation."""
        # Create initial
        affiliation = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization,
            raw_text="Initial"
        )
        initial_id = affiliation.id
        
        # Update
        updated = self.ArticleAffiliation.create_or_update(
            user=self.user,
            article=self.article,
            organization=self.organization,
            raw_text="Updated"
        )
        
        self.assertEqual(updated.id, initial_id)
        self.assertEqual(updated.raw_text, "Updated")
        self.assertEqual(self.ArticleAffiliation.objects.count(), 1)
    
    def test_article_affiliation_str_with_organization(self):
        """Test string representation with organization."""
        affiliation = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization
        )
        
        expected = f"{self.article} - {self.organization}"
        self.assertEqual(str(affiliation), expected)
    
    def test_article_affiliation_str_with_raw_name(self):
        """Test string representation with raw institution name."""
        affiliation = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            raw_institution_name="Test Institution"
        )
        
        expected = f"{self.article} - Test Institution"
        self.assertEqual(str(affiliation), expected)
    
    def test_article_affiliation_str_with_raw_text(self):
        """Test string representation with raw text."""
        affiliation = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            raw_text="Raw Text Organization"
        )
        
        expected = f"{self.article} - Raw Text Organization"
        self.assertEqual(str(affiliation), expected)
    
    def test_article_affiliation_requires_article(self):
        """Test that article is required."""
        with self.assertRaises(ValueError):
            self.ArticleAffiliation.create(
                user=self.user,
                article=None,
                organization=self.organization
            )
    
    def test_article_affiliation_parental_key_cascade(self):
        """Test that deleting article cascades to affiliation."""
        affiliation = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization
        )
        
        article_id = self.article.id
        affiliation_id = affiliation.id
        
        # Delete article
        self.article.delete()
        
        # Check affiliation is also deleted
        self.assertFalse(
            self.ArticleAffiliation.objects.filter(id=affiliation_id).exists()
        )
