from unittest.mock import patch
from django.test import TestCase

from .exceptions import OrganizationCreateOrUpdateError
from .models import Organization, OrganizationInstitutionType
from .tasks import (
    task_children_migrate_data,
    task_migrate_date_institution_to_organization_publisher,
)
from core.users.models import User
from journal.models import PublisherHistory, CopyrightHolderHistory
from institution.models import (
    Institution,
    InstitutionIdentification,
    Publisher,
    CopyrightHolder,
)
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
            user=self.user,
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
        self.assertEqual(
            self.organization.institution_type_scielo.first(),
            self.institution_type_scielo,
        )
        self.assertEqual(self.organization.location.country.name, "Brasil")
        self.assertEqual(self.organization.is_official, True)

    def test_create_or_update_organization_fail(self):
        with self.assertRaises(OrganizationCreateOrUpdateError):
            self.organization = Organization.create_or_update(
                name=None,
                user=self.user,
                acronym=self.institution.institution_identification.acronym,
                url=self.institution.url,
                location=self.location,
                institution_type_scielo=self.institution_type_scielo,
                institution_type_mec="institution_type_mec",
                is_official=True,
            )


class OrganizationTaskTest(TestCase):
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
        self.publisher_history = PublisherHistory.get_or_create(
            user=self.user,
            institution=self.publisher,
        )
        self.coyright = CopyrightHolderHistory.get_or_create(
            user=self.user,
            institution=self.coyright,
        )

    @patch("organization.tasks.task_children_migrate_data.apply_async")
    def test_migration_data_institution_publisher_to_organization(
        self, mock_apply_async
    ):
        result = task_migrate_date_institution_to_organization_publisher(
            user_id=None,
            username="teste",
            model="PublisherHistory",
            collection=None,
            journal=None,
        )
        print(self.publisher_history.id)
        mock_apply_async.assert_called_once_with(
            kwargs=dict(
                user_id=None,
                username="teste",
                model_institutition="PublisherHistory",
                model_institutition_id=self.publisher_history.id,
                institution_data={
                    "institution__name": "Name of institution",
                    "institution__acronym": "Acronym of institution",
                    "institution__is_official": True,
                    "institution__level_1": "level_1",
                    "institution__level_2": "level_2",
                    "institution__level_3": "level_3",
                    "institution__url": "www.teste.com.br",
                    "institution__type": "organização sem fins de lucros",
                    "institution__type_scielo": None,
                    "location_id": self.location.id,
                },
            )
        )
        called_kwargs = mock_apply_async.call_args[1]["kwargs"]
        self.assertEqual(
            called_kwargs["institution_data"].get("institution__name"),
            "Name of institution",
        )
        self.assertEqual(
            called_kwargs["institution_data"].get("institution__acronym"),
            "Acronym of institution",
        )
        self.assertEqual(
            called_kwargs["institution_data"].get("institution__type"),
            "organização sem fins de lucros",
        )
        self.assertEqual(
            called_kwargs["institution_data"].get("institution__level_1"), "level_1"
        )
        self.assertEqual(
            called_kwargs["institution_data"].get("institution__level_2"), "level_2"
        )
        self.assertEqual(
            called_kwargs["institution_data"].get("institution__level_3"), "level_3"
        )
        self.assertEqual(
            called_kwargs["institution_data"].get("institution__url"),
            "www.teste.com.br",
        )

        task_children_migrate_data(**called_kwargs)

        organization = Organization.objects.first()
        org_level = self.publisher_history.org_level.first()

        self.assertEqual(organization.name, "Name of institution")
        self.assertEqual(organization.acronym, "Acronym of institution")
        self.assertEqual(
            organization.institution_type_mec, "organização sem fins de lucros"
        )
        self.assertEqual(organization.url, "www.teste.com.br")
        self.assertEqual(org_level.level_1, "level_1")
        self.assertEqual(org_level.level_2, "level_2")
        self.assertEqual(org_level.level_3, "level_3")

        self.publisher_history.refresh_from_db()
        self.assertEqual(self.publisher_history.organization, organization)

    def test_migration_multiple_data_institution_publisher_to_organization(self):
        args = dict(
            user_id=None,
            username="teste",
            model_institutition="PublisherHistory",
            model_institutition_id=self.publisher_history.id,
            institution_data={
                "institution__name": "Name of institution",
                "institution__acronym": "Acronym of institution",
                "institution__is_official": True,
                "institution__level_1": "level_1",
                "institution__level_2": "level_2",
                "institution__level_3": "level_3",
                "institution__url": "www.teste.com.br",
                "institution__type": "organização sem fins de lucros",
                "institution__type_scielo": None,
                "location_id": self.location.id,
            },
        )
        task_children_migrate_data(**args)
        task_children_migrate_data(**args)

        organization = Organization.objects.all()
        publisher_history = PublisherHistory.objects.all()
        self.assertEqual(organization.count(), 1)
        self.assertEqual(publisher_history.count(), 1)
        self.assertEqual(publisher_history.first().organization, organization.first())
