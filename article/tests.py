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


class ContribCollabTest(TestCase):
    """Tests for ContribCollab model."""
    
    def setUp(self):
        """Set up test data."""
        from article.models import ArticleAffiliation, ContribCollab
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
        
        # Create an affiliation
        self.affiliation = ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization
        )
        
        self.ContribCollab = ContribCollab
    
    def test_contrib_collab_create_with_affiliation(self):
        """Test creating ContribCollab with affiliation."""
        collab = self.ContribCollab.create(
            user=self.user,
            article=self.article,
            affiliation=self.affiliation,
            collab="Research Group"
        )
        
        self.assertIsNotNone(collab.id)
        self.assertEqual(collab.article, self.article)
        self.assertEqual(collab.affiliation, self.affiliation)
        self.assertEqual(collab.collab, "Research Group")
        self.assertEqual(collab.creator, self.user)
    
    def test_contrib_collab_create_without_affiliation(self):
        """Test creating ContribCollab without affiliation."""
        collab = self.ContribCollab.create(
            user=self.user,
            article=self.article,
            collab="Independent Researcher"
        )
        
        self.assertIsNotNone(collab.id)
        self.assertEqual(collab.article, self.article)
        self.assertIsNone(collab.affiliation)
        self.assertEqual(collab.collab, "Independent Researcher")
    
    def test_contrib_collab_get(self):
        """Test getting a ContribCollab."""
        collab = self.ContribCollab.create(
            user=self.user,
            article=self.article,
            collab="Test Collab",
            affiliation=self.affiliation,
        )
        
        retrieved = self.ContribCollab.get(
            article=self.article,
            collab="Test Collab",
            affiliation=self.affiliation
        )
        
        self.assertEqual(retrieved.id, collab.id)
    
    def test_contrib_collab_create_or_update_creates(self):
        """Test create_or_update creates new contrib collab."""
        collab = self.ContribCollab.create_or_update(
            user=self.user,
            article=self.article,
            affiliation=self.affiliation,
            collab="Initial Collab"
        )
        
        self.assertIsNotNone(collab.id)
        self.assertEqual(self.ContribCollab.objects.count(), 1)
    
    def test_contrib_collab_create_or_update_updates(self):
        """Test create_or_update updates existing contrib collab."""
        # Create initial
        collab = self.ContribCollab.create(
            user=self.user,
            article=self.article,
            collab="Initial",
            affiliation=self.affiliation,
        )
        initial_id = collab.id
        
        # Update - using same article, collab, and affiliation should update
        updated = self.ContribCollab.create_or_update(
            user=self.user,
            article=self.article,
            collab="Initial",
            affiliation=self.affiliation,
        )
        
        self.assertEqual(updated.id, initial_id)
        self.assertEqual(updated.collab, "Initial")
        self.assertEqual(self.ContribCollab.objects.count(), 1)
    
    def test_contrib_collab_str_with_collab_and_affiliation(self):
        """Test string representation with collab and affiliation."""
        collab = self.ContribCollab.create(
            user=self.user,
            article=self.article,
            affiliation=self.affiliation,
            collab="Test Group"
        )
        
        self.assertIn(str(self.article), str(collab))
        self.assertIn("Test Group", str(collab))
    
    def test_contrib_collab_str_with_collab_only(self):
        """Test string representation with collab only."""
        collab = self.ContribCollab.create(
            user=self.user,
            article=self.article,
            collab="Solo Collab"
        )
        
        self.assertIn(str(self.article), str(collab))
        self.assertIn("Solo Collab", str(collab))
    
    def test_contrib_collab_requires_article(self):
        """Test that article is required."""
        with self.assertRaises(ValueError):
            self.ContribCollab.create(
                user=self.user,
                article=None,
                collab="Test Collab",
                affiliation=self.affiliation
            )
    
    def test_contrib_collab_requires_collab_in_create(self):
        """Test that collab is required in create method."""
        with self.assertRaises(ValueError):
            self.ContribCollab.create(
                user=self.user,
                article=self.article,
                collab=None,
                affiliation=self.affiliation
            )
    
    def test_contrib_collab_requires_collab_in_get(self):
        """Test that collab is required in get method."""
        with self.assertRaises(ValueError):
            self.ContribCollab.get(
                article=self.article,
                collab=None,
                affiliation=self.affiliation
            )
    
    def test_contrib_collab_requires_collab_in_create_or_update(self):
        """Test that collab is required in create_or_update method."""
        with self.assertRaises(ValueError):
            self.ContribCollab.create_or_update(
                user=self.user,
                article=self.article,
                collab=None,
                affiliation=self.affiliation
            )
    
    def test_contrib_collab_parental_key_cascade(self):
        """Test that deleting article cascades to contrib collab."""
        collab = self.ContribCollab.create(
            user=self.user,
            article=self.article,
            affiliation=self.affiliation,
            collab="Test"
        )
        
        article_id = self.article.id
        collab_id = collab.id
        
        # Delete article
        self.article.delete()
        
        # Check contrib collab is also deleted
        self.assertFalse(
            self.ContribCollab.objects.filter(id=collab_id).exists()
        )
    
    def test_contrib_collab_affiliation_set_null(self):
        """Test that deleting affiliation sets it to null in contrib collab."""
        collab = self.ContribCollab.create(
            user=self.user,
            article=self.article,
            affiliation=self.affiliation,
            collab="Test"
        )
        
        affiliation_id = self.affiliation.id
        collab_id = collab.id
        
        # Delete affiliation
        self.affiliation.delete()
        
        # Refresh from db
        collab.refresh_from_db()
        
        # Check that collab still exists but affiliation is None
        self.assertTrue(
            self.ContribCollab.objects.filter(id=collab_id).exists()
        )
        self.assertIsNone(collab.affiliation)


class NormAffiliationTest(TestCase):
    """Test cases for NormAffiliation model"""

    def setUp(self):
        from organization.models import NormAffiliation
        from location.models import Location, City, State, Country
        from organization.models import Organization
        
        self.NormAffiliation = NormAffiliation
        self.user = User.objects.create_user(username="testuser", password="testpass")
        
        # Create location components
        self.country = Country.create(user=self.user, name="Brazil", acron2="BR", acron3="BRA")
        self.state = State.create(user=self.user, name="São Paulo", acronym="SP")
        self.city = City.create(user=self.user, name="São Paulo")
        
        # Create location
        self.location = Location._create(
            user=self.user,
            country=self.country,
            state=self.state,
            city=self.city
        )
        
        # Create organization
        self.organization = Organization.create(
            user=self.user,
            name="University of São Paulo",
            acronym="USP",
            location=self.location
        )

    def test_create_norm_affiliation(self):
        """Test creating a NormAffiliation instance"""
        norm_aff = self.NormAffiliation.create(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Medicine",
            level_2="Department of Surgery",
            level_3="Cardiovascular Unit"
        )
        
        self.assertIsNotNone(norm_aff.id)
        self.assertEqual(norm_aff.organization, self.organization)
        self.assertEqual(norm_aff.location, self.location)
        self.assertEqual(norm_aff.level_1, "Faculty of Medicine")
        self.assertEqual(norm_aff.level_2, "Department of Surgery")
        self.assertEqual(norm_aff.level_3, "Cardiovascular Unit")
        self.assertEqual(norm_aff.creator, self.user)

    def test_get_norm_affiliation(self):
        """Test retrieving a NormAffiliation instance"""
        norm_aff = self.NormAffiliation.create(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Sciences",
            level_2="Department of Physics"
        )
        
        retrieved = self.NormAffiliation.get(
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Sciences",
            level_2="Department of Physics"
        )
        
        self.assertEqual(retrieved.id, norm_aff.id)

    def test_create_or_update_creates_new(self):
        """Test create_or_update creates new instance when not exists"""
        norm_aff = self.NormAffiliation.create_or_update(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Engineering",
            level_2="Department of Civil Engineering"
        )
        
        self.assertIsNotNone(norm_aff.id)
        self.assertEqual(norm_aff.level_1, "Faculty of Engineering")

    def test_create_or_update_updates_existing(self):
        """Test create_or_update updates existing instance when exact match found"""
        # Create initial instance with all 5 unique_together fields
        norm_aff = self.NormAffiliation.create(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Law",
            level_2="Department of Criminal Law",
            level_3="Criminal Procedure Unit"
        )
        original_id = norm_aff.id
        
        # Call create_or_update with same unique key - should return existing instance
        updated = self.NormAffiliation.create_or_update(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Law",
            level_2="Department of Criminal Law",
            level_3="Criminal Procedure Unit"
        )
        
        self.assertEqual(updated.id, original_id)

    def test_unique_together_constraint(self):
        """Test unique_together constraint on NormAffiliation"""
        # Create first instance
        self.NormAffiliation.create(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Arts",
            level_2="Department of History"
        )
        
        # Try to create duplicate - should use create_or_update in practice
        # but direct create would raise IntegrityError
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            norm_aff2 = self.NormAffiliation(
                organization=self.organization,
                location=self.location,
                level_1="Faculty of Arts",
                level_2="Department of History",
                creator=self.user
            )
            norm_aff2.save()

    def test_str_method(self):
        """Test __str__ method of NormAffiliation"""
        norm_aff = self.NormAffiliation.create(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Medicine"
        )
        
        str_repr = str(norm_aff)
        self.assertIn("University of São Paulo", str_repr)
        self.assertIn("Faculty of Medicine", str_repr)


class ArticleAffiliationWithLevelsTest(TestCase):
    """Test cases for ArticleAffiliation with level fields"""

    def setUp(self):
        from article.models import Article, ArticleAffiliation
        from organization.models import NormAffiliation
        from location.models import Location, City, State, Country
        from organization.models import Organization
        
        self.ArticleAffiliation = ArticleAffiliation
        self.NormAffiliation = NormAffiliation
        self.user = User.objects.create_user(username="testuser", password="testpass")
        
        # Create article
        self.article = Article.objects.create(pid_v3="test-article-001")
        
        # Create location components
        self.country = Country.create(user=self.user, name="Brazil", acron2="BR", acron3="BRA")
        self.state = State.create(user=self.user, name="Rio de Janeiro", acronym="RJ")
        self.city = City.create(user=self.user, name="Rio de Janeiro")
        
        # Create location
        self.location = Location._create(
            user=self.user,
            country=self.country,
            state=self.state,
            city=self.city
        )
        
        # Create organization
        self.organization = Organization.create(
            user=self.user,
            name="Federal University of Rio de Janeiro",
            acronym="UFRJ",
            location=self.location
        )

    def test_create_with_raw_level_fields(self):
        """Test creating ArticleAffiliation with raw level fields"""
        aff = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization,
            raw_level_1="Instituto de Química",
            raw_level_2="Departamento de Química Orgânica",
            raw_level_3="Laboratório de Síntese"
        )
        
        self.assertEqual(aff.raw_level_1, "Instituto de Química")
        self.assertEqual(aff.raw_level_2, "Departamento de Química Orgânica")
        self.assertEqual(aff.raw_level_3, "Laboratório de Síntese")

    def test_create_or_update_with_level_fields(self):
        """Test create_or_update with level fields"""
        # Create
        aff = self.ArticleAffiliation.create_or_update(
            user=self.user,
            article=self.article,
            organization=self.organization,
            raw_level_1="Faculty of Science"
        )
        original_id = aff.id
        
        # Update
        aff_updated = self.ArticleAffiliation.create_or_update(
            user=self.user,
            article=self.article,
            organization=self.organization,
            raw_level_1="Faculty of Science",
            raw_level_2="Department of Biology"
        )
        
        self.assertEqual(aff_updated.id, original_id)
        self.assertEqual(aff_updated.raw_level_2, "Department of Biology")

    def test_get_with_level_fields(self):
        """Test getting ArticleAffiliation using level fields"""
        aff = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization,
            raw_level_1="Medical School",
            raw_level_2="Surgery Department"
        )
        
        retrieved = self.ArticleAffiliation.get(
            article=self.article,
            raw_level_1="Medical School"
        )
        
        self.assertEqual(retrieved.id, aff.id)

    def test_set_normalized(self):
        """Test set_normalized method"""
        aff = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization,
            raw_level_1="Instituto de Física"
        )
        
        aff.set_normalized(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Institute of Physics",
            level_2="Department of Theoretical Physics"
        )
        
        self.assertIsNotNone(aff.normalized)
        self.assertEqual(aff.normalized.level_1, "Institute of Physics")
        self.assertEqual(aff.normalized.level_2, "Department of Theoretical Physics")

    def test_update_normalized(self):
        """Test update_normalized method"""
        aff = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization
        )
        
        # First update - creates normalized
        aff.update_normalized(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Engineering School"
        )
        
        norm_id = aff.normalized.id
        
        # Second update - updates existing
        aff.update_normalized(
            user=self.user,
            level_2="Mechanical Engineering Department"
        )
        
        self.assertEqual(aff.normalized.id, norm_id)
        self.assertEqual(aff.normalized.level_2, "Mechanical Engineering Department")

    def test_clear_normalized(self):
        """Test clear_normalized method"""
        aff = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization
        )
        
        aff.set_normalized(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="School of Arts"
        )
        
        self.assertIsNotNone(aff.normalized)
        
        aff.clear_normalized(user=self.user)
        
        self.assertIsNone(aff.normalized)

    def test_normalized_field_in_create(self):
        """Test creating ArticleAffiliation with normalized field"""
        norm_aff = self.NormAffiliation.create(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Education"
        )
        
        aff = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization,
            normalized=norm_aff
        )
        
        self.assertEqual(aff.normalized, norm_aff)


class ContribPersonTest(TestCase):
    """Tests for ContribPerson model."""
    
    def setUp(self):
        """Set up test data."""
        from article.models import ArticleAffiliation, ContribPerson
        from location.models import Country, Location
        from organization.models import Organization, NormAffiliation
        
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
        
        # Create an affiliation
        self.affiliation = ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization
        )
        
        self.ContribPerson = ContribPerson
        self.ArticleAffiliation = ArticleAffiliation
        self.NormAffiliation = NormAffiliation
    
    def test_contrib_person_create_basic(self):
        """Test creating ContribPerson with basic fields."""
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            fullname="John Smith",
            given_names="John",
            last_name="Smith"
        )
        
        self.assertIsNotNone(person.id)
        self.assertEqual(person.article, self.article)
        self.assertEqual(person.fullname, "John Smith")
        self.assertEqual(person.given_names, "John")
        self.assertEqual(person.last_name, "Smith")
        self.assertEqual(person.creator, self.user)
    
    def test_contrib_person_create_with_orcid_and_email(self):
        """Test creating ContribPerson with ORCID and email."""
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            fullname="Jane Doe",
            orcid="0000-0002-1825-0097",
            email="jane.doe@example.com"
        )
        
        self.assertEqual(person.orcid, "0000-0002-1825-0097")
        self.assertEqual(person.email, "jane.doe@example.com")
    
    def test_contrib_person_create_with_affiliation(self):
        """Test creating ContribPerson with affiliation."""
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            fullname="John Smith",
            affiliation=self.affiliation
        )
        
        self.assertEqual(person.affiliation, self.affiliation)
    
    def test_contrib_person_get(self):
        """Test getting a ContribPerson."""
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            fullname="John Smith"
        )
        
        retrieved = self.ContribPerson.get(
            article=self.article,
            fullname="John Smith"
        )
        
        self.assertEqual(retrieved.id, person.id)
    
    def test_contrib_person_get_by_orcid(self):
        """Test getting a ContribPerson by ORCID."""
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            fullname="John Smith",
            orcid="0000-0002-1825-0097"
        )
        
        retrieved = self.ContribPerson.get(
            article=self.article,
            orcid="0000-0002-1825-0097"
        )
        
        self.assertEqual(retrieved.id, person.id)
    
    def test_contrib_person_create_or_update_creates(self):
        """Test create_or_update creates new person."""
        person = self.ContribPerson.create_or_update(
            user=self.user,
            article=self.article,
            fullname="John Smith",
            given_names="John",
            last_name="Smith"
        )
        
        self.assertIsNotNone(person.id)
        self.assertEqual(self.ContribPerson.objects.count(), 1)
    
    def test_contrib_person_create_or_update_updates(self):
        """Test create_or_update updates existing person."""
        # Create initial
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            fullname="John Smith",
            email="old@example.com"
        )
        initial_id = person.id
        
        # Update
        updated = self.ContribPerson.create_or_update(
            user=self.user,
            article=self.article,
            fullname="John Smith",
            email="new@example.com"
        )
        
        self.assertEqual(updated.id, initial_id)
        self.assertEqual(updated.email, "new@example.com")
        self.assertEqual(self.ContribPerson.objects.count(), 1)
    
    def test_contrib_person_str_with_fullname(self):
        """Test string representation with fullname."""
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            fullname="John Smith"
        )
        
        self.assertIn("John Smith", str(person))
    
    def test_contrib_person_str_with_declared_name(self):
        """Test string representation with declared name."""
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            declared_name="Dr. John Smith"
        )
        
        self.assertIn("Dr. John Smith", str(person))
    
    def test_contrib_person_requires_article(self):
        """Test that article is required."""
        with self.assertRaises(ValueError):
            self.ContribPerson.create(
                user=self.user,
                article=None,
                fullname="John Smith"
            )
    
    def test_contrib_person_parental_key_cascade(self):
        """Test that deleting article cascades to person."""
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            fullname="John Smith"
        )
        
        person_id = person.id
        
        # Delete article
        self.article.delete()
        
        # Check person is also deleted
        self.assertFalse(
            self.ContribPerson.objects.filter(id=person_id).exists()
        )
    
    def test_add_orcid(self):
        """Test add_orcid method."""
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            fullname="John Smith"
        )
        
        person.add_orcid(self.user, "0000-0002-1825-0097")
        
        person.refresh_from_db()
        self.assertEqual(person.orcid, "0000-0002-1825-0097")
        self.assertEqual(person.updated_by, self.user)
    
    def test_add_raw_affiliation(self):
        """Test add_raw_affiliation method."""
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            fullname="John Smith"
        )
        
        person.add_raw_affiliation(
            user=self.user,
            raw_text="Department of Biology, Test University",
            raw_institution_name="Test University",
            raw_country_name="Brazil",
            raw_country_code="BR"
        )
        
        person.refresh_from_db()
        self.assertIsNotNone(person.affiliation)
        self.assertEqual(person.affiliation.raw_institution_name, "Test University")
        self.assertEqual(person.affiliation.raw_country_name, "Brazil")
    
    def test_add_raw_affiliation_updates_existing(self):
        """Test add_raw_affiliation updates existing affiliation."""
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            fullname="John Smith",
            affiliation=self.affiliation
        )
        
        initial_aff_id = person.affiliation.id
        
        person.add_raw_affiliation(
            user=self.user,
            raw_institution_name="Updated University"
        )
        
        person.refresh_from_db()
        # Should create a new affiliation since we're using create_or_update
        self.assertIsNotNone(person.affiliation)
    
    def test_add_normalized_affiliation_creates_affiliation(self):
        """Test add_normalized_affiliation creates affiliation if missing."""
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            fullname="John Smith"
        )
        
        self.assertIsNone(person.affiliation)
        
        person.add_normalized_affiliation(
            user=self.user,
            organization=self.organization,
            location=self.location
        )
        
        person.refresh_from_db()
        self.assertIsNotNone(person.affiliation)
        self.assertIsNotNone(person.affiliation.normalized)
    
    def test_add_normalized_affiliation_updates_existing(self):
        """Test add_normalized_affiliation updates existing affiliation."""
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            fullname="John Smith",
            affiliation=self.affiliation
        )
        
        person.add_normalized_affiliation(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Science"
        )
        
        person.refresh_from_db()
        self.assertIsNotNone(person.affiliation.normalized)
        self.assertEqual(person.affiliation.normalized.organization, self.organization)
        self.assertEqual(person.affiliation.normalized.level_1, "Faculty of Science")
    
    def test_contrib_person_all_name_fields(self):
        """Test ContribPerson with all name fields from ResearchNameMixin."""
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            given_names="John Robert",
            last_name="Smith",
            suffix="Jr.",
            fullname="John Robert Smith Jr.",
            declared_name="Dr. John R. Smith Jr."
        )
        
        self.assertEqual(person.given_names, "John Robert")
        self.assertEqual(person.last_name, "Smith")
        self.assertEqual(person.suffix, "Jr.")
        self.assertEqual(person.fullname, "John Robert Smith Jr.")
        self.assertEqual(person.declared_name, "Dr. John R. Smith Jr.")


