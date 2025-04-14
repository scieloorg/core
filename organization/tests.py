from unittest.mock import patch
from django.test import TestCase

from .exceptions import OrganizationGetError
from .models import Organization, OrganizationInstitutionType
from .tasks import task_children_migrate_data, task_migrate_date_institution_to_organization_publisher
from core.users.models import User
from institution.models import Institution, InstitutionIdentification, Publisher, CopyrightHolder
from location.models import Location


class OrganizationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="teste", password="teste")
        self.institution_identification = InstitutionIdentification.objects.create(
            name="Name of institution",
            acronym="Acronym of institution",
            is_official=True,
        )
        self.location = Location.create_or_update(
            user=self.user,
            city_name="Fortaleza",
            state_name="Ceará",
            state_acronym="CE",
            country_name="Brasil",
            country_acronym="BR",
        )
        self.institution = Institution.objects.create(
            creator=self.user,
            institution_identification=self.institution_identification,
            location=self.location,
            url="www.teste.com.br",
            level_1="level_1",
            level_2="level_2",
            level_3="level_3",
            institution_type="organização sem fins de lucros",
        )
        self.institution_type_scielo = OrganizationInstitutionType.create_or_update(
            user=self.user,
            name="institution_type_scielo",
        )
        self.publisher = Publisher.objects.create(
            creator=self.user,
            institution=self.institution,
        )
        self.coyright = CopyrightHolder.objects.create(
            creator=self.user,
            institution=self.institution,
        )

    def test_create_or_update_organization(self):
        self.organization = Organization.create_or_update(
            name=self.institution.institution_identification.name,
            acronym=self.institution.institution_identification.acronym,
            url=self.institution.url,
            location=self.location,
            institution_type_scielo=self.institution_type_scielo,
            institution_type_mec="institution_type_mec",
            is_official=True,
        )

        self.assertEqual(self.organization.name, "Name of institution")
        self.assertEqual(self.organization.acronym, "Acronym of institution")
        self.assertEqual(self.organization.url, "www.teste.com.br")
        self.assertEqual(self.organization.institution_type_mec, "institution_type_mec")
        self.assertEqual(self.organization.institution_type_scielo.first(), self.institution_type_scielo)
        self.assertEqual(self.organization.location.country.name, "Brasil")
        self.assertEqual(self.organization.is_official, True)  
        
    def test_create_or_update_organization_fail(self):
        with self.assertRaises(OrganizationGetError):
            self.organization = Organization.create_or_update(
                name=None,
                acronym=self.institution.institution_identification.acronym,
                url=self.institution.url,
                location=self.location,
                institution_type_scielo=self.institution_type_scielo,
                institution_type_mec="institution_type_mec",
                is_official=True,
            )

