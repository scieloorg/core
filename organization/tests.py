from unittest.mock import patch
from django.test import TestCase

from .models import OrganizationPublisher, OrganizationOwner, OrganizationInstitutionType, OrganizationCopyrightHolder
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

    def test_create_or_update_organization_publisher(self):
        self.publisher = OrganizationPublisher.create_or_update(
            name=self.institution.institution_identification.name,
            acronym=self.institution.institution_identification.acronym,
            url=self.institution.url,
            level_1=self.institution.level_1,
            level_2=self.institution.level_2,
            level_3=self.institution.level_3,
            institution_type_scielo=self.institution_type_scielo,
            institution_type_mec="institution_type_mec",
        )

        self.assertEqual(self.publisher.name, "Name of institution")
        self.assertEqual(self.publisher.acronym, "Acronym of institution")
        self.assertEqual(self.publisher.url, "www.teste.com.br")
        self.assertEqual(self.publisher.org_level.first().level_1, "level_1")
        self.assertEqual(self.publisher.org_level.first().level_2, "level_2")
        self.assertEqual(self.publisher.org_level.first().level_3, "level_3")
        self.assertEqual(self.publisher.institution_type_mec, "institution_type_mec")
        self.assertEqual(self.publisher.institution_type_scielo.first(), self.institution_type_scielo)
        
    def test_create_or_update_organization_owner(self):
        self.publisher = OrganizationOwner.create_or_update(
            name=self.institution.institution_identification.name,
            acronym=self.institution.institution_identification.acronym,
            url=self.institution.url,
            level_1=self.institution.level_1,
            level_2=self.institution.level_2,
        )

        self.assertEqual(self.publisher.name, "Name of institution")
        self.assertEqual(self.publisher.acronym, "Acronym of institution")
        self.assertEqual(self.publisher.url, "www.teste.com.br")
        self.assertEqual(self.publisher.org_level.first().level_1, "level_1")
        self.assertEqual(self.publisher.org_level.first().level_2, "level_2")
        self.assertEqual(self.publisher.org_level.first().level_3, None)

    @patch("organization.tasks.task_children_migrate_data.apply_async")
    def test_migration_data_institution_publisher_to_organization(self, mock_applyt_async):
        result = task_migrate_date_institution_to_organization_publisher(
            user_id=None, 
            username="teste", 
            model="Publisher", 
            collection=None, 
            journal=None,
        )
        mock_applyt_async.assert_called_once_with(
            user_id=None,
            username="teste",
            model="Publisher",
            location_id=self.location.id,
            **{
                'institution__name': 'Name of institution', 
                'institution__acronym': 'Acronym of institution', 
                'institution__is_official': True, 
                'institution__level_1': 'level_1', 
                'institution__level_2': 'level_2', 
                'institution__level_3': 'level_3', 
                'institution__url': 'www.teste.com.br', 
                'institution__type': "organização sem fins de lucros", 
                'institution__type_scielo': None
            }
        )
        called_kwargs = mock_applyt_async.call_args[1]
        self.assertEqual(called_kwargs.get("institution__name"), 'Name of institution')
        self.assertEqual(called_kwargs.get("institution__acronym"), 'Acronym of institution')
        self.assertEqual(called_kwargs.get("institution__type"), "organização sem fins de lucros")
        self.assertEqual(called_kwargs.get("institution__level_1"), "level_1")
        self.assertEqual(called_kwargs.get("institution__level_2"), "level_2")
        self.assertEqual(called_kwargs.get("institution__level_3"), "level_3")
        self.assertEqual(called_kwargs.get("institution__url"), "www.teste.com.br")
        
        task_children_migrate_data(**called_kwargs)

        organization_publisher = OrganizationPublisher.objects.first()
        self.assertEqual(organization_publisher.name, "Name of institution")
        self.assertEqual(organization_publisher.acronym, "Acronym of institution")
        self.assertEqual(organization_publisher.institution_type_mec, "organização sem fins de lucros")
        self.assertEqual(organization_publisher.org_level.first().level_1, "level_1")
        self.assertEqual(organization_publisher.org_level.first().level_2, "level_2")
        self.assertEqual(organization_publisher.org_level.first().level_3, "level_3")
        self.assertEqual(organization_publisher.url, "www.teste.com.br")        


    @patch("organization.tasks.task_children_migrate_data.apply_async")
    def test_migration_data_institution_publisher_to_organization(self, mock_applyt_async):
        result = task_migrate_date_institution_to_organization_publisher(
            user_id=None, 
            username="teste", 
            model="CopyrightHolder", 
            collection=None, 
            journal=None,
        )
        mock_applyt_async.assert_called_once_with(
            user_id=None,
            username="teste",
            model="CopyrightHolder",
            location_id=self.location.id,
            **{
                'institution__name': 'Name of institution', 
                'institution__acronym': 'Acronym of institution', 
                'institution__is_official': True, 
                'institution__level_1': 'level_1', 
                'institution__level_2': 'level_2', 
                'institution__level_3': 'level_3', 
                'institution__url': 'www.teste.com.br', 
                'institution__type': "organização sem fins de lucros", 
                'institution__type_scielo': None
            }
        )
        called_kwargs = mock_applyt_async.call_args[1]
        self.assertEqual(called_kwargs.get("institution__name"), 'Name of institution')
        self.assertEqual(called_kwargs.get("institution__acronym"), 'Acronym of institution')
        self.assertEqual(called_kwargs.get("institution__type"), "organização sem fins de lucros")
        self.assertEqual(called_kwargs.get("institution__level_1"), "level_1")
        self.assertEqual(called_kwargs.get("institution__level_2"), "level_2")
        self.assertEqual(called_kwargs.get("institution__level_3"), "level_3")
        self.assertEqual(called_kwargs.get("institution__url"), "www.teste.com.br")
        
        task_children_migrate_data(**called_kwargs)

        organization_copyright = OrganizationCopyrightHolder.objects.first()
        self.assertEqual(organization_copyright.name, "Name of institution")
        self.assertEqual(organization_copyright.acronym, "Acronym of institution")
        self.assertEqual(organization_copyright.institution_type_mec, "organização sem fins de lucros")
        self.assertEqual(organization_copyright.org_level.first().level_1, "level_1")
        self.assertEqual(organization_copyright.org_level.first().level_2, "level_2")
        self.assertEqual(organization_copyright.org_level.first().level_3, "level_3")
        self.assertEqual(organization_copyright.url, "www.teste.com.br")
