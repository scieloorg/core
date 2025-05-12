from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from core.models import Gender
from core.users.models import User
from location.models import Location
from organization.models import Organization
from researcher.models import (
    Affiliation,
    NewResearcher,
    PersonName,
    Researcher,
    ResearcherIds,
    ResearcherOrcid,
)

from .tasks import (
    children_migrate_old_researcher_to_new_researcher,
    migrate_old_researcher_to_new_researcher,
)


class PersonNameJoinNameTest(SimpleTestCase):
    def test_person_name_join_name(self):
        test_cases = [
            (["Palavra1", None, None], "Palavra1"),
            (["Palavra1", "Palavra2", None], "Palavra1 Palavra2"),
            (["Palavra1", "Palavra2", "Palavra3"], "Palavra1 Palavra2 Palavra3"),
        ]

        for text, expected in test_cases:
            with self.subTest(text=text, excepted=expected):
                result = PersonName.join_names(*text)
                self.assertEqual(expected, result)


class ResearcherOrcidTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="teste", password="teste")

    def test_researcher_orcid_create(self):
        ResearcherOrcid.get_or_create(
            user=self.user,
            orcid="0000-0002-9147-0547",
        )
        researcher_orcid = ResearcherOrcid.objects.all()
        self.assertEqual(researcher_orcid.count(), 1)
        self.assertEqual(researcher_orcid.first().orcid, "0000-0002-9147-0547")

    def test_researcher_orcid_create_two_times(self):
        ResearcherOrcid.get_or_create(
            user=self.user,
            orcid="0000-0002-9147-0547",
        )
        ResearcherOrcid.get_or_create(
            user=self.user,
            orcid="0000-0002-9147-0547",
        )
        researcher_orcid = ResearcherOrcid.objects.all()
        self.assertEqual(researcher_orcid.count(), 1)
        self.assertEqual(researcher_orcid.first().orcid, "0000-0002-9147-0547")

    def test_researcher_orcid_create_wrong_orcid_https(self):
        ResearcherOrcid.get_or_create(
            user=self.user,
            orcid="https://orcid.org/0000-0002-9147-0547",
        )
        researcher_orcid = ResearcherOrcid.objects.all()
        self.assertEqual(researcher_orcid.count(), 1)
        self.assertEqual(researcher_orcid.first().orcid, "0000-0002-9147-0547")

    def test_researcher_orcid_create_wrong_orcid_http(self):
        ResearcherOrcid.get_or_create(
            user=self.user,
            orcid="http://orcid.org/0000-0002-9147-0547",
        )
        researcher_orcid = ResearcherOrcid.objects.all()
        self.assertEqual(researcher_orcid.count(), 1)
        self.assertEqual(researcher_orcid.first().orcid, "0000-0002-9147-0547")


class NewResearcherTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="teste", password="teste")
        # ParentalKey
        self.researcher_id_orcid = ResearcherOrcid.get_or_create(
            user=self.user,
            orcid="0000-0002-9147-0547",
        )
        self.researcher_id_orcid_2 = ResearcherOrcid.get_or_create(
            user=self.user,
            orcid="0000-0002-9147-0548",
        )        

        self.location = Location.create_or_update(
            user=self.user,
            city_name="Campinas",
            country_text="Brasil",
            country_acronym="BR",
            country_name=None,
            state_text="São Paulo",
            state_acronym="SP",
            state_name=None,
        )
        self.organization = Organization.create_or_update(
            user=self.user,
            name="Name of institution",
            acronym="Acronym of institution",
            url="www.teste.com.br",
            location=self.location,
            institution_type_mec="institution_type_mec",
            is_official=True,
        )
        self.organization_2 = Organization.create_or_update(
            user=self.user,
            name="Name of institution 2",
            acronym="Acronym of institution 2",
            url="www.teste2.com.br",
            location=self.location,
            institution_type_mec="institution_type_mec",
            is_official=True,
        )

    @staticmethod
    def get_or_create_researcher(user, given_names, last_name, suffix, orcid=None, affiliation=None):
        return NewResearcher.get_or_create(
            user=user,
            given_names=given_names,
            last_name=last_name,
            suffix=suffix,
            orcid=orcid,
            affiliation=affiliation,
        )

    @staticmethod
    def get_or_create_researcher_id(user, researcher, identifier, source_name):
        return ResearcherIds.get_or_create(
            user=user,
            researcher=researcher,
            identifier=identifier,
            source_name=source_name,
        )

    def test_researcher_orcid_create_with_wrong_orcid(self):
        with self.assertRaises(ValidationError):
            ResearcherOrcid.get_or_create(
                user=self.user,
                orcid="0000-0002-9147",
            )

    def test_new_researcher_create(self):
        researcher = self.get_or_create_researcher(
            user=self.user,
            given_names="Anna",
            last_name="Carla",
            suffix="Jr.",
            affiliation=self.organization,
            orcid=self.researcher_id_orcid,
        )
        self.get_or_create_researcher_id(
            user=self.user,
            researcher=researcher,
            identifier="user.teste@dom.org",
            source_name="EMAIL",
        )
        researcher = NewResearcher.objects.all()
        self.assertEqual(researcher.count(), 1)
        self.assertEqual(researcher[0].given_names, "Anna")
        self.assertEqual(researcher[0].last_name, "Carla")
        self.assertEqual(researcher[0].suffix, "Jr.")
        self.assertEqual(researcher[0].researcher_ids.count(), 1)
        self.assertEqual(
            researcher[0].researcher_ids.first().identifier, "user.teste@dom.org"
        )
        self.assertEqual(researcher[0].orcid.orcid, "0000-0002-9147-0547")
        self.assertEqual(researcher[0].affiliation, self.organization)

    def test_researcher_id_create_with_wrong_email(self):
        researcher = self.get_or_create_researcher(
            user=self.user,
            given_names="Anna",
            last_name="Carla",
            suffix="Jr.",
            affiliation=self.organization,
            orcid=self.researcher_id_orcid,
        )

        with self.assertRaises(ValidationError):
            ResearcherIds.get_or_create(
                user=self.user,
                researcher=researcher,
                identifier="user.teste",
                source_name="EMAIL",
            )

    def test_researcher_id_create_with_wrong_lattes(self):
        researcher = self.get_or_create_researcher(
            user=self.user,
            given_names="Anna",
            last_name="Carla",
            suffix="Jr.",
            affiliation=self.organization,
            orcid=self.researcher_id_orcid,
        )

        with self.assertRaises(ValidationError):
            ResearcherIds.get_or_create(
                user=self.user,
                researcher=researcher,
                identifier="user.teste",
                source_name="EMAIL",
            )

    def test_new_researcher_create_two_times(self):
        researcher_1 = self.get_or_create_researcher(
            user=self.user,
            given_names="Anna",
            last_name="Carla",
            suffix="Jr.",
            affiliation=self.organization,
            orcid=self.researcher_id_orcid,
        )
        researcher_2 = self.get_or_create_researcher(
            user=self.user,
            given_names="Anna",
            last_name="Carla",
            suffix="Jr.",
            affiliation=self.organization,
            orcid=self.researcher_id_orcid,
        )
        researcher_id_email_1 = self.get_or_create_researcher_id(
            user=self.user,
            researcher=researcher_1,
            identifier="user.teste@dom.org",
            source_name="EMAIL",
        )
        researcher_id_email_2 = self.get_or_create_researcher_id(
            user=self.user,
            researcher=researcher_2,
            identifier="user.teste@dom.org",
            source_name="EMAIL",
        )

        researcher = NewResearcher.objects.all()
        self.assertEqual(researcher.count(), 1)
        self.assertEqual(researcher[0].given_names, "Anna")
        self.assertEqual(researcher[0].last_name, "Carla")
        self.assertEqual(researcher[0].suffix, "Jr.")
        self.assertEqual(researcher[0].researcher_ids.count(), 1)
        self.assertEqual(
            researcher[0].researcher_ids.first().identifier, "user.teste@dom.org"
        )
        self.assertEqual(researcher[0].orcid.orcid, "0000-0002-9147-0547")
        self.assertEqual(researcher[0].affiliation, self.organization)
        self.assertEqual(researcher[0].affiliation, self.organization)
        self.assertEqual(ResearcherIds.objects.all().count(), 1)
        self.assertEqual(researcher_id_email_1, researcher_id_email_2)
        self.assertEqual(researcher_1, researcher_2)

    def test_new_researcher_create_without_orcid(self):
        researcher = self.get_or_create_researcher(
            user=self.user,
            given_names="Anna",
            last_name="Carla",
            suffix="Jr.",
            affiliation=self.organization,
        )
        self.get_or_create_researcher_id(
            user=self.user,
            researcher=researcher,
            identifier="user.teste@dom.org",
            source_name="EMAIL",
        )
        researcher = NewResearcher.objects.all()
        self.assertEqual(researcher.count(), 1)
        self.assertEqual(researcher[0].given_names, "Anna")
        self.assertEqual(researcher[0].last_name, "Carla")
        self.assertEqual(researcher[0].suffix, "Jr.")
        self.assertEqual(researcher[0].researcher_ids.count(), 1)
        self.assertEqual(
            researcher[0].researcher_ids.first().identifier, "user.teste@dom.org"
        )
        self.assertEqual(researcher[0].orcid, None)

    def test_new_researcher_create_two_times_different_name_same_orcid(self):
        researcher_1 = self.get_or_create_researcher(
            user=self.user,
            given_names="Anna",
            last_name="Carla",
            suffix="Jr.",
            affiliation=self.organization,
            orcid=self.researcher_id_orcid,
        )
        self.get_or_create_researcher_id(
            user=self.user,
            researcher=researcher_1,
            identifier="user.teste@dom.org",
            source_name="EMAIL",
        )
        researcher_2 = self.get_or_create_researcher(
            user=self.user,
            given_names="Anna2",
            last_name="Carla2",
            suffix="Jr2.",
            affiliation=self.organization_2,
            orcid=self.researcher_id_orcid,
        )
        self.get_or_create_researcher_id(
            user=self.user,
            researcher=researcher_2,
            identifier="user.teste2@dom.org",
            source_name="EMAIL",
        )        
        researcher = NewResearcher.objects.all()
        self.assertEqual(researcher.count(), 2)
        self.assertEqual(researcher[0].given_names, "Anna")
        self.assertEqual(researcher[0].last_name, "Carla")
        self.assertEqual(researcher[0].suffix, "Jr.")
        self.assertEqual(researcher[0].researcher_ids.count(), 1)
        self.assertEqual(
            researcher[0].researcher_ids.first().identifier, "user.teste@dom.org"
        )
        self.assertEqual(researcher[0].orcid.orcid, "0000-0002-9147-0547")
        self.assertEqual(researcher[1].given_names, "Anna2")
        self.assertEqual(researcher[1].last_name, "Carla2")
        self.assertEqual(researcher[1].suffix, "Jr2.")
        self.assertEqual(researcher[1].researcher_ids.count(), 1)
        self.assertEqual(
            researcher[1].researcher_ids.first().identifier, "user.teste2@dom.org"
        )
        self.assertEqual(researcher[0].orcid.orcid, researcher[1].orcid.orcid) 

    def test_new_researcher_create_two_times_same_name_different_orcid(self):
        researcher_1 = self.get_or_create_researcher(
            user=self.user,
            given_names="Anna",
            last_name="Carla",
            suffix="Jr.",
            affiliation=self.organization,
            orcid=self.researcher_id_orcid,
        )
        self.get_or_create_researcher_id(
            user=self.user,
            researcher=researcher_1,
            identifier="user.teste@dom.org",
            source_name="EMAIL",
        )
        researcher_2 = self.get_or_create_researcher(
            user=self.user,
            given_names="Anna",
            last_name="Carla",
            suffix="Jr.",
            affiliation=self.organization_2,
            orcid=self.researcher_id_orcid_2,
        )
        self.get_or_create_researcher_id(
            user=self.user,
            researcher=researcher_2,
            identifier="user.teste@dom.org",
            source_name="EMAIL",
        )
        researcher = NewResearcher.objects.all()
        self.assertEqual(researcher.count(), 2)
        self.assertEqual(researcher[0].given_names, "Anna")
        self.assertEqual(researcher[0].last_name, "Carla")
        self.assertEqual(researcher[0].suffix, "Jr.")
        self.assertEqual(researcher[0].researcher_ids.count(), 1)
        self.assertEqual(researcher[0].orcid.orcid, "0000-0002-9147-0547")
        self.assertEqual(
            researcher[0].researcher_ids.first().identifier, "user.teste@dom.org"
        )
        self.assertEqual(researcher[1].given_names, "Anna")
        self.assertEqual(researcher[1].last_name, "Carla")
        self.assertEqual(researcher[1].suffix, "Jr.")
        self.assertEqual(researcher[1].researcher_ids.count(), 1)
        self.assertEqual(
            researcher[1].researcher_ids.first().identifier, "user.teste@dom.org"
        )
        self.assertEqual(researcher[1].orcid.orcid, "0000-0002-9147-0548")
        self.assertNotEqual(researcher[0], researcher[1])
        
    def test_new_researcher_create_without_orcid_same_affiliation(self):
        researcher_1 = self.get_or_create_researcher(
            user=self.user,
            given_names="Anna",
            last_name="Carla",
            suffix="Jr.",
            affiliation=self.organization,
        )
        self.get_or_create_researcher_id(
            user=self.user,
            researcher=researcher_1,
            identifier="user.test@dom.org",
            source_name="EMAIL",
        )
        researcher_2 = self.get_or_create_researcher(
            user=self.user,
            given_names="Anna",
            last_name="Carla",
            suffix="Jr.",
            affiliation=self.organization,
        )
        researcher = NewResearcher.objects.all()
        self.assertEqual(researcher.count(), 1)
        self.assertEqual(researcher[0].given_names, "Anna")
        self.assertEqual(researcher[0].last_name, "Carla")
        self.assertEqual(researcher[0].suffix, "Jr.")
        self.assertEqual(researcher[0].researcher_ids.count(), 1)
        self.assertEqual(
            researcher[0].researcher_ids.first().identifier, "user.test@dom.org"
        )
        self.assertEqual(researcher[0].orcid, None)
        self.assertEqual(researcher_1, researcher_2)
        self.assertEqual(researcher_1.affiliation, self.organization)
        self.assertEqual(researcher_1.affiliation, researcher_2.affiliation)
        self.assertEqual(researcher_1, researcher_2)


class MigrationResearcherTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="teste", password="teste")
        self.gender = Gender.create_or_update(user=self.user, code="F", gender="F")
        self.location = Location.create_or_update(
            user=self.user,
            city_name="Campinas",
            country_text="Brasil",
            country_acronym="BR",
            country_name=None,
            state_text="São Paulo",
            state_acronym="SP",
            state_name=None,
        )
        self.affiliation = Affiliation.create_or_update(
            user=self.user,
            name="Universidade Federal de São Carlos",
            acronym="UFSC",
            url="www.teste.com.br",
            location=self.location,
            institution_type="agência de apoio à pesquisa",
            official=None,
            is_official=True,
            level_1=None,
            level_2=None,
            level_3=None,
        )
        self.researcher = Researcher.create_or_update(
            self.user,
            given_names="Anna",
            last_name="Taomeaome",
            suffix="Jr.",
            declared_name="Anna Taomeaome",
            lattes="qwertpoiuytkdiekd",
            orcid="1234-1234-0987-0987",
            email="user@dom.org",
            gender=self.gender,
            gender_identification_status="DECLARED",
            affiliation=self.affiliation,
        )

    def get_args(
        self,
    ):
        return dict(
            username=self.user.username,
            user_id=None,
            data=dict(
                given_names="Anna",
                last_name="Taomeaome",
                suffix="Jr.",
                declared_name="Anna Taomeaome",
                orcid="1234-1234-0987-0987",
                source_name="ORCID",
                affiliation_name="Universidade Federal de São Carlos",
                affiliation_acronym="UFSC",
                affiliation_is_official=True,
                institution_type="agência de apoio à pesquisa",
                institution_url="www.teste.com.br",
                location_id=self.researcher.affiliation.institution.location.id,
            ),
        )

    @patch(
        "researcher.tasks.children_migrate_old_researcher_to_new_researcher.apply_async"
    )
    def test_migrate_old_researcher_to_new_researcher_assert_called(
        self, mock_apply_async
    ):
        migrate_old_researcher_to_new_researcher(username=self.user.username)
        mock_apply_async.assert_called_once_with(
            kwargs=self.get_args(),
        )

    def test_task_children_migrate_old_researcher_to_new_researcher(self):
        args = self.get_args()
        children_migrate_old_researcher_to_new_researcher(**args)

        new_researcher = NewResearcher.objects.all()
        self.assertEqual(new_researcher.count(), 1)
        self.assertEqual(new_researcher[0].given_names, "Anna")
        self.assertEqual(new_researcher[0].last_name, "Taomeaome")
        self.assertEqual(new_researcher[0].suffix, "Jr.")
        self.assertEqual(new_researcher[0].fullname, "Anna Taomeaome Jr.")
        self.assertEqual(new_researcher[0].researcher_ids.count(), 1)
        self.assertEqual(
            new_researcher[0].researcher_ids.first().identifier, "1234-1234-0987-0987"
        )
        self.assertEqual(new_researcher[0].researcher_ids.first().source_name, "ORCID")
        self.assertEqual(
            new_researcher[0].affiliation.name, "Universidade Federal de São Carlos"
        )
        self.assertEqual(new_researcher[0].affiliation.acronym, "UFSC")
        self.assertEqual(new_researcher[0].affiliation.is_official, True)
        self.assertEqual(
            new_researcher[0].affiliation.institution_type_mec,
            "agência de apoio à pesquisa",
        )
        self.assertEqual(new_researcher[0].affiliation.url, "www.teste.com.br")

        organization = Organization.objects.all()
        self.assertEqual(organization.count(), 1)

    def test_called_two_times_task_children_migrate_old_researcher_to_new_researcher(
        self,
    ):
        args = self.get_args()
        children_migrate_old_researcher_to_new_researcher(**args)
        children_migrate_old_researcher_to_new_researcher(**args)

        new_researcher = NewResearcher.objects.all()
        self.assertEqual(new_researcher.count(), 1)
        self.assertEqual(new_researcher[0].given_names, "Anna")
        self.assertEqual(new_researcher[0].last_name, "Taomeaome")
        self.assertEqual(new_researcher[0].suffix, "Jr.")
        self.assertEqual(new_researcher[0].fullname, "Anna Taomeaome Jr.")
        self.assertEqual(new_researcher[0].researcher_ids.count(), 1)
        self.assertEqual(
            new_researcher[0].researcher_ids.first().identifier, "1234-1234-0987-0987"
        )
        self.assertEqual(new_researcher[0].researcher_ids.first().source_name, "ORCID")
        self.assertEqual(
            new_researcher[0].affiliation.name, "Universidade Federal de São Carlos"
        )
        self.assertEqual(new_researcher[0].affiliation.acronym, "UFSC")
        self.assertEqual(new_researcher[0].affiliation.is_official, True)
        self.assertEqual(
            new_researcher[0].affiliation.institution_type_mec,
            "agência de apoio à pesquisa",
        )
        self.assertEqual(new_researcher[0].affiliation.url, "www.teste.com.br")

        organization = Organization.objects.all()
        self.assertEqual(organization.count(), 1)
