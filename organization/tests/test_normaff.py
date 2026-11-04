import unittest

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from organization.models import NormAffiliation
from organization.tests.test_mixins import OrganizationTestMixin

User = get_user_model()


class NormAffiliationTest(OrganizationTestMixin, TestCase):
    """Test cases for NormAffiliation model"""

    def setUp(self):
        self.NormAffiliation = NormAffiliation
        self.user = User.objects.create_user(username="testuser", password="testpass")

        self.location = self.make_location(self.user)
        self.organization = self.make_organization(
            self.user,
            name="University of São Paulo",
            location=self.location,
        )

    def test_create_norm_affiliation(self):
        norm_aff = self.NormAffiliation.create(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Medicine",
            level_2="Department of Surgery",
            level_3="Cardiovascular Unit",
        )
        self.assertIsNotNone(norm_aff.id)
        self.assertEqual(norm_aff.organization, self.organization)
        self.assertEqual(norm_aff.location, self.location)
        self.assertEqual(norm_aff.level_1, "Faculty of Medicine")
        self.assertEqual(norm_aff.level_2, "Department of Surgery")
        self.assertEqual(norm_aff.level_3, "Cardiovascular Unit")
        self.assertEqual(norm_aff.creator, self.user)

    def test_get_norm_affiliation(self):
        norm_aff = self.NormAffiliation.create(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Sciences",
            level_2="Department of Physics",
        )
        retrieved = self.NormAffiliation.get(
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Sciences",
            level_2="Department of Physics",
        )
        self.assertEqual(retrieved.id, norm_aff.id)

    def test_create_or_update_creates_new(self):
        norm_aff = self.NormAffiliation.create_or_update(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Engineering",
            level_2="Department of Civil Engineering",
        )
        self.assertIsNotNone(norm_aff.id)
        self.assertEqual(norm_aff.level_1, "Faculty of Engineering")

    def test_create_or_update_updates_existing(self):
        norm_aff = self.NormAffiliation.create(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Law",
            level_2="Department of Criminal Law",
            level_3="Criminal Procedure Unit",
        )
        original_id = norm_aff.id

        updated = self.NormAffiliation.create_or_update(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Law",
            level_2="Department of Criminal Law",
            level_3="Criminal Procedure Unit",
        )
        self.assertEqual(updated.id, original_id)

    @unittest.skip(
        "TODO: O model NormAffiliation não possui unique_together "
        "configurado. Ajustar o model e a migration antes de reativar este "
        "teste."
    )
    def test_unique_together_constraint(self):
        self.NormAffiliation.create(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Arts",
            level_2="Department of History",
        )

        with self.assertRaises(IntegrityError):
            norm_aff2 = self.NormAffiliation.create(
                user=self.user,
                organization=self.organization,
                location=self.location,
                level_1="Faculty of Arts",
                level_2="Department of History",
            )
            norm_aff2.save()

    def test_str_method(self):
        norm_aff = self.NormAffiliation.create(
            user=self.user,
            organization=self.organization,
            location=self.location,
            level_1="Faculty of Medicine",
        )
        str_repr = str(norm_aff)
        self.assertIn("University of São Paulo", str_repr)
        self.assertIn("Faculty of Medicine", str_repr)