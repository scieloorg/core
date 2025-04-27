from unittest.mock import patch

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from wagtail.documents.models import Document

# Create your tests here.

from core.models import Gender
from location.models import Location
from editorialboard.models import (
    EditorialBoardMember,
    EditorialBoardMemberFile,
)
from editorialboard.views import import_file_ebm
from researcher.models import NewResearcher, ResearcherIds
from organization.models import Organization
from journal.models import Journal

from django.core.files.uploadedfile import SimpleUploadedFile
User = get_user_model()


class EditorialBoardMemberTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="user")
        self.journal = Journal.objects.create(title="Revista XXXX")
        self.gender = Gender.create_or_update(user=self.user, code="F", gender="F")
        self.location = Location.create_or_update(
            self.user,
            city_name="São Paulo",
            country_text="Brasil",
            country_acronym="BR",
            country_name=None,
            state_name="São Paulo",
            state_acronym="SP",
        )
        self.organization = Organization.create_or_update(
            user=self.user,
            name="Name of institution",
            acronym="Acronym of institution",
            url="www.teste.com.br",
            location=self.location,
            institution_type_mec="outros",
            is_official=True,
        )
        self.researcher_identifier_orcid = ResearcherIds.get_or_create(
            user=self.user,
            identifier="0000-0002-9147-0547",
            source_name="ORCID",
        )
        self.researcher_identifier_lattes = ResearcherIds.get_or_create(
            user=self.user,
            identifier="qwertpoiuytkdiekd",
            source_name="LATTES",
        )
        self.researcher_identifier_email = ResearcherIds.get_or_create(
            user=self.user,
            identifier="user@dom.org",
            source_name="EMAIL",
        )
        self.researcher = NewResearcher.get_or_create(
            self.user,
            given_names="Anna",
            last_name="Taomeaome",
            suffix="Jr.",
            researcher_identifier=self.researcher_identifier_orcid,
            affiliation=self.organization,
            gender=self.gender,
            gender_identification_status="DECLARED",
        )
        self.researcher = NewResearcher.get_or_create(
            self.user,
            given_names="Anna",
            last_name="Taomeaome",
            suffix="Jr.",
            researcher_identifier=self.researcher_identifier_email,
            affiliation=self.organization,
            gender=self.gender,
            gender_identification_status="DECLARED",
        )
        self.researcher = NewResearcher.get_or_create(
            self.user,
            given_names="Anna",
            last_name="Taomeaome",
            suffix="Jr.",
            researcher_identifier=self.researcher_identifier_lattes,
            affiliation=self.organization,
            gender=self.gender,
            gender_identification_status="DECLARED",
        )

    def test_create_or_update_location(self):
        self.assertEqual("Brasil", self.location.country.name)
        self.assertEqual("São Paulo", self.location.city.name)
        self.assertEqual("SP", self.location.state.acronym)

    def test_create_or_update_researcher(self):
        editorial_board_member = EditorialBoardMember.create_or_update(
            user=self.user,
            researcher=self.researcher,
            journal=self.journal,
            declared_role="editor de seção",
            std_role=None,
            editorial_board_initial_year="2010-03-01",
            editorial_board_final_year="2012-03-01",
        )
        self.assertEqual(
            "São Paulo", editorial_board_member.researcher.affiliation.location.state.name
        )
        self.assertEqual(
            "São Paulo", editorial_board_member.researcher.affiliation.location.city.name
        )
        self.assertEqual(
            "Brasil", editorial_board_member.researcher.affiliation.location.country.name
        )
        self.assertEqual(
            "Name of institution",
            editorial_board_member.researcher.affiliation.name,
        )
        self.assertEqual("F", editorial_board_member.researcher.gender.code)
        self.assertEqual("F", editorial_board_member.researcher.gender.gender)
        self.assertEqual(
            "DECLARED", editorial_board_member.researcher.gender_identification_status
        )
        self.assertEqual("Anna Taomeaome Jr.", editorial_board_member.researcher.fullname)

        self.assertEqual(
            "qwertpoiuytkdiekd",
            editorial_board_member.researcher.researcher_ids.filter(source_name="LATTES").first().identifier,
        )

        self.assertEqual(
            "0000-0002-9147-0547",
            editorial_board_member.researcher.researcher_ids.filter(source_name="ORCID").first().identifier,
        )
        self.assertEqual(
            "user@dom.org",
            editorial_board_member.researcher.researcher_ids.filter(source_name="EMAIL").first().identifier,
        )

    def test_editorial_board_member_create_or_update(self):
        editorial_board = EditorialBoardMember.create_or_update(
            user=self.user,
            journal=self.journal,
            researcher=self.researcher,
            declared_role="editor de seção",
            editorial_board_initial_year="2010-01-01",
            editorial_board_final_year="2012-01-01",
        )
        self.assertEqual(self.researcher, editorial_board.researcher)
        self.assertEqual("Revista XXXX", editorial_board.journal.title)
        self.assertEqual(1, EditorialBoardMember.objects.get(journal=self.journal).role_editorial_board.count())
        self.assertEqual("editor de seção", EditorialBoardMember.objects.get(journal=self.journal).role_editorial_board.first().role.declared_role)


class ImportFileEBMTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="user")
        self.journal = Journal.objects.create(title="Revista XXXX")
        self.csv_content = """Nome do membro;Sobrenome;Periódico;Suffix;declared_person_name;CV Lattes;ORCID iD;Email;Gender;institution_city_name;institution_state_text;institution_state_acronym;institution_state_name;institution_country_text;institution_country_acronym;institution_country_name;institution_div1;institution_div2;Instituição;Cargo / instância do membro;Data
John;Doe;Revista XXXX;Jr;John Doe;lattes;0000-0000-0000-0000;john@doe.com;M;City;State;ST;State Name;Country;CN;Country Name;Div1;Div2;Institution;Editor;2020"""
        self.factory = RequestFactory()
   
    def create_editorial_file(self, csv_content):
        csv_file = SimpleUploadedFile(
            name="test.csv",
            content=csv_content.encode("utf-8"),
            content_type="text/csv",
        )
        document = Document.objects.create(title="Test CSV", file=csv_file)

        return EditorialBoardMemberFile.objects.create(attachment=document)
    
    def add_messages_middleware(self, request):
        """Add session and messages middleware to the request."""
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware

        # Pass a dummy get_response function to the middleware
        SessionMiddleware(lambda req: None).process_request(request)
        MessageMiddleware(lambda req: None).process_request(request)
        request.session.save()
        request._messages = FallbackStorage(request)
        return request

    def test_import_file_edm(self):
        editorial_file = self.create_editorial_file(self.csv_content)
        request = self.factory.get(f"/import-ebm/?file_id={editorial_file.pk}")      
        request.user = self.user
        request.META["HTTP_REFERER"] = "/some-valid-url/"
        request = self.add_messages_middleware(request)
        response = import_file_ebm(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Location.objects.all().count(), 1)
        self.assertEqual(Researcher.objects.all().count(), 1)
        self.assertEqual(EditorialBoardMember.objects.all().count(), 1)
        self.assertEqual(EditorialBoardMember.objects.first().researcher.person_name.fullname, "John Doe Jr")
        self.assertEqual(EditorialBoardMember.objects.first().journal.title, "Revista XXXX")
        self.assertEqual(EditorialBoardMember.objects.first().role_editorial_board.first().role.declared_role, "Editor")
        self.assertEqual(EditorialBoardMember.objects.first().role_editorial_board.first().initial_year, "2020")
        self.assertEqual(EditorialBoardMember.objects.first().role_editorial_board.first().final_year, "2020")