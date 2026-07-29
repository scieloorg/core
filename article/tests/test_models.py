from datetime import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.timezone import make_aware
from freezegun import freeze_time

from article import choices
from article.models import Article, ArticleAffiliation, ContribCollab, ContribPerson
from article.tests.test_mixins import ArticleTestMixin
from organization.models import NormAffiliation
from organization.tests.test_mixins import OrganizationTestMixin

User = get_user_model()


class RemoveDuplicateArticlesTest(ArticleTestMixin, TestCase):
    """Testes de deduplicação de artigos."""

    def setUp(self):
        self.user = User.objects.create_user(username="dedup_user", password="x")

    def create_article_at_time(self, dt, sps_pkg_name):
        with freeze_time(dt):
            return Article.objects.create(
                sps_pkg_name=sps_pkg_name,
                creator=self.user,
                created=make_aware(datetime.strptime(dt, "%Y-%m-%d")),
            )

    def test_marks_most_recent_as_deduplicated_when_none_available(self):
        self.create_article_at_time("2023-01-01", "pkg1")
        self.create_article_at_time("2023-01-02", "pkg1")
        most_recent = self.create_article_at_time("2023-01-03", "pkg1")

        with patch.object(Article, "check_availability", return_value=False):
            Article.deduplicate_items(user=self.user, deduplicate=True)

        self.assertEqual(Article.objects.filter(sps_pkg_name="pkg1").count(), 3)
        most_recent.refresh_from_db()
        self.assertEqual(most_recent.data_status, choices.DATA_STATUS_DEDUPLICATED)

    def test_stops_at_first_available_starting_from_most_recent(self):
        oldest = self.create_article_at_time("2023-01-01", "pkg2")
        newest = self.create_article_at_time("2023-01-02", "pkg2")

        def fake_check_availability(self_article, user, force_update=False):
            return self_article.id == oldest.id

        with patch.object(Article, "check_availability", fake_check_availability):
            Article.deduplicate_items(user=self.user, deduplicate=True)

        oldest.refresh_from_db()
        newest.refresh_from_db()
        self.assertNotEqual(oldest.data_status, choices.DATA_STATUS_DEDUPLICATED)
        self.assertNotEqual(newest.data_status, choices.DATA_STATUS_DEDUPLICATED)

    def test_marks_all_matching_as_duplicated(self):
        a1 = self.create_article_at_time("2022-06-03", "pkg3")
        a2 = self.create_article_at_time("2022-06-04", "pkg3")

        Article.deduplicate_items(user=self.user, mark_as_duplicated=True)

        a1.refresh_from_db()
        a2.refresh_from_db()
        self.assertEqual(a1.data_status, choices.DATA_STATUS_DUPLICATED)
        self.assertEqual(a2.data_status, choices.DATA_STATUS_DUPLICATED)

    def test_no_action_if_only_one_article(self):
        self.create_article_at_time("2023-01-01", "pkg4")

        Article.deduplicate_items(
            user=self.user, mark_as_duplicated=True, deduplicate=True
        )

        self.assertEqual(Article.objects.filter(sps_pkg_name="pkg4").count(), 1)


class ArticleAffiliationTest(ArticleTestMixin, OrganizationTestMixin, TestCase):
    """Tests for ArticleAffiliation model."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.organization = self.make_organization(self.user)
        self.article = self.make_article(user=self.user)
        self.ArticleAffiliation = ArticleAffiliation

    def test_article_affiliation_create_with_organization(self):
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
        affiliation = self.ArticleAffiliation.create_or_update(
            user=self.user,
            article=self.article,
            organization=self.organization,
            raw_text="Initial"
        )
        self.assertIsNotNone(affiliation.id)
        self.assertEqual(self.ArticleAffiliation.objects.count(), 1)

    def test_article_affiliation_create_or_update_updates(self):
        affiliation = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization,
            raw_text="Initial"
        )
        initial_id = affiliation.id

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
        affiliation = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization
        )
        expected = f"{self.article} - {self.organization}"
        self.assertEqual(str(affiliation), expected)

    def test_article_affiliation_str_with_raw_name(self):
        affiliation = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            raw_institution_name="Test Institution"
        )
        expected = f"{self.article} - Test Institution"
        self.assertEqual(str(affiliation), expected)

    def test_article_affiliation_str_with_raw_text(self):
        affiliation = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            raw_text="Raw Text Organization"
        )
        expected = f"{self.article} - Raw Text Organization"
        self.assertEqual(str(affiliation), expected)

    def test_article_affiliation_requires_article(self):
        with self.assertRaises(ValueError):
            self.ArticleAffiliation.create(
                user=self.user,
                article=None,
                organization=self.organization
            )

    def test_article_affiliation_parental_key_cascade(self):
        affiliation = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization
        )
        affiliation_id = affiliation.id
        self.article.delete()
        self.assertFalse(
            self.ArticleAffiliation.objects.filter(id=affiliation_id).exists()
        )


class ContribCollabTest(ArticleTestMixin, OrganizationTestMixin, TestCase):
    """Tests for ContribCollab model."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.organization = self.make_organization(self.user)
        self.article = self.make_article(user=self.user)
        self.affiliation = ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization
        )
        self.ContribCollab = ContribCollab

    def test_contrib_collab_create_with_affiliation(self):
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
        collab = self.ContribCollab.create_or_update(
            user=self.user,
            article=self.article,
            affiliation=self.affiliation,
            collab="Initial Collab"
        )
        self.assertIsNotNone(collab.id)
        self.assertEqual(self.ContribCollab.objects.count(), 1)

    def test_contrib_collab_create_or_update_updates(self):
        collab = self.ContribCollab.create(
            user=self.user,
            article=self.article,
            collab="Initial",
            affiliation=self.affiliation,
        )
        initial_id = collab.id

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
        collab = self.ContribCollab.create(
            user=self.user,
            article=self.article,
            affiliation=self.affiliation,
            collab="Test Group"
        )
        self.assertIn(str(self.article), str(collab))
        self.assertIn("Test Group", str(collab))

    def test_contrib_collab_str_with_collab_only(self):
        collab = self.ContribCollab.create(
            user=self.user,
            article=self.article,
            collab="Solo Collab"
        )
        self.assertIn(str(self.article), str(collab))
        self.assertIn("Solo Collab", str(collab))

    def test_contrib_collab_requires_article(self):
        with self.assertRaises(ValueError):
            self.ContribCollab.create(
                user=self.user,
                article=None,
                collab="Test Collab",
                affiliation=self.affiliation
            )

    def test_contrib_collab_requires_collab_in_create(self):
        with self.assertRaises(ValueError):
            self.ContribCollab.create(
                user=self.user,
                article=self.article,
                collab=None,
                affiliation=self.affiliation
            )

    def test_contrib_collab_requires_collab_in_get(self):
        with self.assertRaises(ValueError):
            self.ContribCollab.get(
                article=self.article,
                collab=None,
                affiliation=self.affiliation
            )

    def test_contrib_collab_requires_collab_in_create_or_update(self):
        with self.assertRaises(ValueError):
            self.ContribCollab.create_or_update(
                user=self.user,
                article=self.article,
                collab=None,
                affiliation=self.affiliation
            )

    def test_contrib_collab_parental_key_cascade(self):
        collab = self.ContribCollab.create(
            user=self.user,
            article=self.article,
            affiliation=self.affiliation,
            collab="Test"
        )
        collab_id = collab.id
        self.article.delete()
        self.assertFalse(
            self.ContribCollab.objects.filter(id=collab_id).exists()
        )

    def test_contrib_collab_affiliation_set_null(self):
        collab = self.ContribCollab.create(
            user=self.user,
            article=self.article,
            affiliation=self.affiliation,
            collab="Test"
        )
        collab_id = collab.id
        self.affiliation.delete()
        collab.refresh_from_db()

        self.assertTrue(
            self.ContribCollab.objects.filter(id=collab_id).exists()
        )
        self.assertIsNone(collab.affiliation)


class ArticleAffiliationWithLevelsTest(ArticleTestMixin, OrganizationTestMixin, TestCase):
    """Test cases for ArticleAffiliation with level fields"""

    def setUp(self):
        self.ArticleAffiliation = ArticleAffiliation
        self.NormAffiliation = NormAffiliation
        self.user = User.objects.create_user(username="testuser", password="testpass")

        self.article = self.make_article(pid_v3="test-article-001")
        self.location = self.make_location(
            self.user,
            state_name="Rio de Janeiro",
            state_acronym="RJ",
            city_name="Rio de Janeiro",
        )
        self.organization = self.make_organization(
            self.user,
            name="Federal University of Rio de Janeiro",
            acronym="UFRJ",
            location=self.location,
        )

    def test_create_with_raw_level_fields(self):
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
        aff = self.ArticleAffiliation.create_or_update(
            user=self.user,
            article=self.article,
            organization=self.organization,
            raw_level_1="Faculty of Science"
        )
        original_id = aff.id

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
        aff = self.ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization
        )
        aff.update_normalized(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Engineering School"
        )
        norm_id = aff.normalized.id

        aff.update_normalized(
            user=self.user,
            level_2="Mechanical Engineering Department"
        )
        self.assertEqual(aff.normalized.id, norm_id)
        self.assertEqual(aff.normalized.level_2, "Mechanical Engineering Department")

    def test_clear_normalized(self):
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


class ContribPersonTest(ArticleTestMixin, OrganizationTestMixin, TestCase):
    """Tests for ContribPerson model."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.location = self.make_location(self.user)
        self.organization = self.make_organization(self.user, location=self.location)
        self.article = self.make_article(user=self.user)
        self.affiliation = ArticleAffiliation.create(
            user=self.user,
            article=self.article,
            organization=self.organization
        )
        self.ContribPerson = ContribPerson

    def test_contrib_person_create_basic(self):
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            declared_name="John Smith",
            given_names="John",
            last_name="Smith"
        )
        self.assertIsNotNone(person.id)
        self.assertEqual(person.article, self.article)
        self.assertEqual(person.declared_name, "John Smith")
        self.assertEqual(person.given_names, "John")
        self.assertEqual(person.last_name, "Smith")
        self.assertEqual(person.creator, self.user)

    def test_contrib_person_create_with_orcid_and_email(self):
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            declared_name="Jane Doe",
            orcid="0000-0002-1825-0097",
            email="jane.doe@example.com"
        )
        self.assertEqual(person.orcid, "0000-0002-1825-0097")
        self.assertEqual(person.email, "jane.doe@example.com")

    def test_contrib_person_create_with_affiliation(self):
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            declared_name="John Smith",
            affiliation=self.affiliation
        )
        self.assertEqual(person.affiliation, self.affiliation)

    def test_contrib_person_get(self):
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            declared_name="John Smith"
        )
        retrieved = self.ContribPerson.get(
            article=self.article,
            declared_name="John Smith"
        )
        self.assertEqual(retrieved.id, person.id)

    def test_contrib_person_get_by_orcid(self):
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            declared_name="John Smith",
            orcid="0000-0002-1825-0097"
        )
        retrieved = self.ContribPerson.get(
            article=self.article,
            declared_name="John Smith",
            orcid="0000-0002-1825-0097"
        )
        self.assertEqual(retrieved.id, person.id)

    def test_contrib_person_create_or_update_creates(self):
        person = self.ContribPerson.create_or_update(
            user=self.user,
            article=self.article,
            declared_name="John Smith",
            given_names="John",
            last_name="Smith"
        )
        self.assertIsNotNone(person.id)
        self.assertEqual(self.ContribPerson.objects.count(), 1)

    def test_contrib_person_create_or_update_updates(self):
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            declared_name="John Smith",
            email="old@example.com"
        )
        initial_id = person.id

        updated = self.ContribPerson.create_or_update(
            user=self.user,
            article=self.article,
            declared_name="John Smith",
            email="new@example.com"
        )
        self.assertEqual(updated.id, initial_id)
        self.assertEqual(updated.email, "new@example.com")
        self.assertEqual(self.ContribPerson.objects.count(), 1)

    def test_contrib_person_str_with_fullname(self):
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            declared_name="John Smith"
        )
        self.assertIn("John Smith", str(person))

    def test_contrib_person_str_with_declared_name(self):
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            declared_name="Dr. John Smith"
        )
        self.assertIn("Dr. John Smith", str(person))

    def test_contrib_person_requires_article(self):
        with self.assertRaises(ValueError):
            self.ContribPerson.create(
                user=self.user,
                article=None,
                declared_name="John Smith"
            )

    def test_contrib_person_parental_key_cascade(self):
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            declared_name="John Smith"
        )
        person_id = person.id
        self.article.delete()
        self.assertFalse(
            self.ContribPerson.objects.filter(id=person_id).exists()
        )

    def test_add_orcid(self):
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            declared_name="John Smith"
        )
        person.add_orcid(self.user, "0000-0002-1825-0097")
        person.refresh_from_db()
        self.assertEqual(person.orcid, "0000-0002-1825-0097")
        self.assertEqual(person.updated_by, self.user)

    def test_add_raw_affiliation(self):
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            declared_name="John Smith"
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
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            declared_name="John Smith",
            affiliation=self.affiliation
        )
        person.add_raw_affiliation(
            user=self.user,
            raw_institution_name="Updated University"
        )
        person.refresh_from_db()
        self.assertIsNotNone(person.affiliation)
        self.assertEqual(person.affiliation.raw_institution_name, "Updated University")

    def test_add_normalized_affiliation_creates_affiliation(self):
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            declared_name="John Smith"
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
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            declared_name="John Smith",
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
        person = self.ContribPerson.create(
            user=self.user,
            article=self.article,
            given_names="John Robert",
            last_name="Smith",
            suffix="Jr.",
            declared_name="Dr. John R. Smith Jr."
        )
        self.assertEqual(person.given_names, "John Robert")
        self.assertEqual(person.last_name, "Smith")
        self.assertEqual(person.suffix, "Jr.")
        self.assertEqual(person.declared_name, "Dr. John R. Smith Jr.")