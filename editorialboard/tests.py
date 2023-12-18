import logging

from django.test import TestCase
from django.contrib.auth import get_user_model

# Create your tests here.

from editorialboard.models import (
    EditorialBoardMember,
    EditorialBoardMemberActivity,
    EditorialBoardRole,
    EditorialBoard,
)
from researcher.models import ResearcherAKA
from journal.models import Journal


User = get_user_model()


class EditorialBoardMemberTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="user")
        self.journal = Journal.objects.create(title="Revista XXXX")
        logging.info(self.journal.title)
        logging.info(self.user)

    def test__create_or_update_location(self):

        location = EditorialBoardMember._create_or_update_location(
            self.user,
            city_name="Campinas",
            country_text="Brasil",
            country_acronym=None,
            country_name=None,
            state_text="SP",
            state_acronym=None,
            state_name=None,
        )
        self.assertEqual("Brasil", location.country.name)
        self.assertEqual("Campinas", location.city.name)
        self.assertEqual("SP", location.state.acronym)

    def test_create_or_update_researcher(self):

        researcher = EditorialBoardMember._create_or_update_researcher(
            self.user,
            given_names=None,
            last_name=None,
            suffix=None,
            declared_person_name="Anna Taomeaome",
            lattes="qwertpoiuytkdiekd",
            orcid="1234-1234-0987-0987",
            email="user@dom.org",
            gender_code="F",
            gender_identification_status="DECLARED",
            institution_name="Universidade Federal de São Carlos",
            institution_div1=None,
            institution_div2=None,
            institution_city_name="São Carlos",
            institution_country_text="Brasil",
            institution_country_acronym=None,
            institution_country_name=None,
            institution_state_text="São Paulo",
            institution_state_acronym=None,
            institution_state_name=None,
        )
        self.assertEqual(
            "São Paulo", researcher.affiliation.institution.location.state.name
        )
        self.assertEqual(
            "São Carlos", researcher.affiliation.institution.location.city.name
        )
        self.assertEqual(
            "Brasil", researcher.affiliation.institution.location.country.name
        )
        self.assertEqual(
            "Universidade Federal de São Carlos",
            researcher.affiliation.institution.institution_identification.name,
        )
        self.assertEqual("F", researcher.person_name.gender.code)
        self.assertEqual("F", researcher.person_name.gender.gender)
        self.assertEqual(
            "DECLARED", researcher.person_name.gender_identification_status
        )
        self.assertEqual("Anna Taomeaome", researcher.person_name.declared_name)
        self.assertEqual(
            "qwertpoiuytkdiekd",
            ResearcherAKA.objects.get(
                researcher=researcher, researcher_identifier__source_name="LATTES"
            ).researcher_identifier.identifier,
        )

        self.assertEqual(
            "1234-1234-0987-0987",
            ResearcherAKA.objects.get(
                researcher=researcher, researcher_identifier__source_name="ORCID"
            ).researcher_identifier.identifier,
        )
        self.assertEqual(
            "user@dom.org",
            ResearcherAKA.objects.get(
                researcher=researcher, researcher_identifier__source_name="EMAIL"
            ).researcher_identifier.identifier,
        )

    def test_create_or_update(self):
        member = EditorialBoardMember.create_or_update(
            self.user,
            researcher=None,
            journal=None,
            journal_title="Revista XXXX",
            given_names=None,
            last_name=None,
            suffix=None,
            declared_person_name="Anna Taomeaome",
            lattes="qwertpoiuytkdiekd",
            orcid="1234-1234-0987-0987",
            email="user@dom.org",
            gender_code="F",
            gender_identification_status="DECLARED",
            institution_name="Universidade Federal de São Carlos",
            institution_div1=None,
            institution_div2=None,
            institution_city_name="São Carlos",
            institution_country_text="Brasil",
            institution_country_acronym=None,
            institution_country_name=None,
            institution_state_text="São Paulo",
            institution_state_acronym=None,
            institution_state_name=None,
            declared_role="editor de seção",
            std_role=None,
            member_activity_initial_year="2000",
            member_activity_final_year="2010",
            member_activity_initial_month="01",
            member_activity_final_month="12",
            editorial_board_initial_year="2010",
            editorial_board_final_year="2012",
        )

        self.assertEqual(
            "2000",
            EditorialBoardMemberActivity.objects.get(
                member=member,
                role__declared_role="editor de seção",
                initial_year="2000",
            ).initial_year,
        )
        self.assertEqual(
            "2010", EditorialBoard.objects.get(journal=self.journal).initial_year
        )
        self.assertEqual(
            "2012", EditorialBoard.objects.get(journal=self.journal).final_year
        )

        for item in EditorialBoardRole.objects.get(
            editorial_board__journal=self.journal,
            role__std_role="associate editor",
        ).members.all():
            with self.subTest(item):
                self.assertEqual(
                    "Anna Taomeaome", item.researcher.person_name.declared_name
                )
