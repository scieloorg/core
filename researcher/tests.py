from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from core.models import Gender
from core.users.models import User
from institution.models import Institution
from location.models import Location
from organization.models import Organization
from researcher.models import (
    NewResearcher,
    PersonName,
    Researcher,
    ResearcherIds,
    Affiliation,
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


class NewResearcherTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="teste", password="teste")
        # ParentalKey
        self.researcher_id_orcid = ResearcherIds.get_or_create(
            user=self.user,
            identifier="0000-0002-9147-0547",
            source_name="ORCID",
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
            name="Name of institution",
            acronym="Acronym of institution",
            url="www.teste.com.br",
            location=self.location,
            institution_type_mec="institution_type_mec",
            is_official=True,
        )

    def test_researcher_id_create(self):
        researcher_id = ResearcherIds.get_or_create(
            user=self.user,
            identifier="0000-0002-9147-0547",
            source_name="ORCID",
        )

        self.assertEqual(researcher_id.identifier, "0000-0002-9147-0547")
        self.assertEqual(researcher_id.source_name, "ORCID")

    def test_new_researcher_create(self):
        NewResearcher.get_or_create(
            user=self.user,
            given_names="Given names",
            last_name="Last name",
            suffix="Suffix",
            affiliation=self.organization,
            researcher_identifier=self.researcher_id_orcid,
        )

        NewResearcher.get_or_create(
            user=self.user,
            given_names="Given names",
            last_name="Last name",
            suffix="Suffix",
            affiliation=self.organization,
            researcher_identifier=self.researcher_id_orcid,
        )
        researcher = NewResearcher.objects.all()
        self.assertEqual(researcher.count(), 1)
        self.assertEqual(researcher[0].given_names, "Given names")
        self.assertEqual(researcher[0].last_name, "Last name")
        self.assertEqual(researcher[0].suffix, "Suffix")
        self.assertEqual(researcher[0].researcher_ids.count(), 1)
        self.assertEqual(
            researcher[0].researcher_ids.first().identifier, "0000-0002-9147-0547"
        )

    def test_new_researcher_with_same_orcid_and_different_names(self):
        NewResearcher.get_or_create(
            user=self.user,
            given_names="Given names",
            last_name="Last name",
            suffix="Suffix",
            affiliation=self.organization,
            researcher_identifier=self.researcher_id_orcid,
        )
        NewResearcher.get_or_create(
            user=self.user,
            given_names="Another Given names",
            last_name="Another Last name",
            suffix="Another Suffix",
            affiliation=self.organization,
            researcher_identifier=self.researcher_id_orcid,
        )

        researcher = NewResearcher.objects.all()
        self.assertEqual(researcher.count(), 2)
        self.assertEqual(researcher[0].given_names, "Given names")
        self.assertEqual(researcher[0].last_name, "Last name")
        self.assertEqual(researcher[0].suffix, "Suffix")
        self.assertEqual(researcher[0].researcher_ids.count(), 1)
        self.assertEqual(
            researcher[0].researcher_ids.first().identifier, "0000-0002-9147-0547"
        )
        self.assertEqual(researcher[1].given_names, "Another Given names")
        self.assertEqual(researcher[1].last_name, "Another Last name")
        self.assertEqual(researcher[1].suffix, "Another Suffix")
        self.assertEqual(researcher[1].researcher_ids.count(), 1)
        self.assertEqual(
            researcher[1].researcher_ids.first().identifier, "0000-0002-9147-0547"
        )


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
