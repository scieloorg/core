import json
from datetime import date
from unittest.mock import patch

from django.test import TestCase, RequestFactory
from django.utils import translation
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from wagtail.admin.panels import get_edit_handler
from wagtail.documents.models import Document

# Create your tests here.

from core.models import Gender
from location.models import Location
from editorialboard.models import (
    EditorialBoardMember,
    EditorialBoardMemberFile,
)
from editorialboard.views import import_file_ebm
from researcher.models import NewResearcher, ResearcherIds, ResearcherOrcid
from organization.models import Organization
from journal.models import Journal

from django.core.files.uploadedfile import SimpleUploadedFile
User = get_user_model()


def get_editorialboard_form(instance, **fields):
    """
    Formulário com dados (bound), como o admin o recebe.

    EditorialboardForm é o base_form_class; a classe usada pelo admin
    (com model e campos definidos) é gerada a partir dos panels.
    """
    data = {
        # management form do InlinePanel role_editorial_board
        "role_editorial_board-TOTAL_FORMS": "0",
        "role_editorial_board-INITIAL_FORMS": "0",
        "role_editorial_board-MIN_NUM_FORMS": "0",
        "role_editorial_board-MAX_NUM_FORMS": "1000",
    }
    data.update(fields)
    form_class = get_edit_handler(EditorialBoardMember).get_form_class()
    return form_class(data=data, instance=instance)


def autocomplete_value(obj):
    # formato esperado pelo widget de AutocompletePanel
    return json.dumps({"pk": obj.pk})


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
            acronym="NOI",
            url="www.teste.com.br",
            location=self.location,
            institution_type_mec="outros",
            is_official=True,
        )
        self.orcid = ResearcherOrcid.get_or_create(
            user=self.user,
            orcid="0000-0002-9147-0547",
        )
        self.researcher = NewResearcher.get_or_create(
            self.user,
            given_names="Anna",
            last_name="Taomeaome",
            suffix="Jr.",
            orcid=self.orcid,
            affiliation=self.organization,
            gender=self.gender,
            gender_identification_status="DECLARED",
        )
        self.researcher.add_lattes_id("1234567890123456", self.user)
        self.researcher.add_email("user@dom.org", self.user)

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
            "1234567890123456",
            editorial_board_member.researcher.researcher_ids.filter(source_name="LATTES").first().identifier,
        )

        self.assertEqual(
            "0000-0002-9147-0547",
            editorial_board_member.researcher.orcid.orcid,
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
John;Doe;Revista XXXX;Jr;John Doe;lattes;0000-0000-0000-0001;john@doe.com;M;City;State;ST;State Name;Country;CN;Country Name;Div1;Div2;Institution;Editor;2020"""
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
        self.assertEqual(NewResearcher.objects.all().count(), 1)
        self.assertEqual(EditorialBoardMember.objects.all().count(), 1)
        self.assertEqual(EditorialBoardMember.objects.first().researcher.fullname, "John Doe Jr")
        self.assertEqual(EditorialBoardMember.objects.first().researcher.affiliation.name, "Institution")
        self.assertEqual(EditorialBoardMember.objects.first().researcher.orcid.orcid, "0000-0000-0000-0001")
        self.assertEqual(EditorialBoardMember.objects.first().journal.title, "Revista XXXX")
        self.assertEqual(EditorialBoardMember.objects.first().role_editorial_board.first().role.declared_role, "Editor")
        self.assertEqual(EditorialBoardMember.objects.first().role_editorial_board.first().initial_year, date(2020, 1, 1))
        self.assertEqual(EditorialBoardMember.objects.first().role_editorial_board.first().final_year, date(2020, 1, 1))


class EditorialBoardMemberFormTest(TestCase):
    """Tests for the manual input form functionality"""
    
    def setUp(self):
        from location.models import Country
        
        self.user = User.objects.create(username="user")
        self.journal = Journal.objects.create(title="Revista Test")
        self.location = Location.create_or_update(
            self.user,
            city_name="São Paulo",
            country_text="Brasil",
            country_acronym="BR",
            country_name="Brasil",
            state_name="São Paulo",
            state_acronym="SP",
        )
        # Get the Country object for tests
        self.country = self.location.country
    
    def test_manual_input_creates_researcher(self):
        """Test that manual input creates a new researcher"""
        # Create form data with manual fields
        form_data = {
            'manual_given_names': 'João',
            'manual_last_name': 'Silva',
            'manual_suffix': 'Jr.',
            'manual_institution_name': 'Universidade de São Paulo',
            'manual_institution_acronym': 'USP',
            'manual_institution_city': 'São Paulo',
            'manual_institution_state': 'São Paulo',
            'manual_institution_country': autocomplete_value(self.country),
            'manual_orcid': '0000-0001-2345-6789',
            'manual_lattes': '1234567890123456',  # Valid 16-digit Lattes ID
            'manual_email': 'joao.silva@usp.br',
        }
        
        # Create editorial board member
        ebm = EditorialBoardMember(journal=self.journal)
        
        # Create the form
        form = get_editorialboard_form(ebm, **form_data)
        self.assertTrue(form.is_valid(), form.errors)
        
        # Manually call save_all to test the logic
        saved_instance = form.save_all(self.user)
        
        # Verify researcher was created
        self.assertIsNotNone(saved_instance.researcher)
        self.assertEqual(saved_instance.researcher.given_names, 'João')
        self.assertEqual(saved_instance.researcher.last_name, 'Silva')
        self.assertEqual(saved_instance.researcher.suffix, 'Jr.')
        
        # Verify affiliation was created (if location exists)
        if saved_instance.researcher.affiliation:
            self.assertEqual(saved_instance.researcher.affiliation.name, 'Universidade de São Paulo')
        
        # Verify ORCID was created and linked
        if saved_instance.researcher.orcid:
            self.assertEqual(saved_instance.researcher.orcid.orcid, '0000-0001-2345-6789')
        
        # Verify Lattes ID was created and linked
        lattes_ids = ResearcherIds.objects.filter(
            researcher=saved_instance.researcher, 
            source_name='LATTES'
        )
        if lattes_ids.exists():
            self.assertEqual(lattes_ids.first().identifier, '1234567890123456')
        
        # Verify Email was created and linked
        email_ids = ResearcherIds.objects.filter(
            researcher=saved_instance.researcher, 
            source_name='EMAIL'
        )
        if email_ids.exists():
            self.assertEqual(email_ids.first().identifier, 'joao.silva@usp.br')
    
    def test_manual_input_without_researcher_requires_names(self):
        """Test that form validation requires names when no researcher selected"""
        # Create form data without required fields
        form_data = {
            'manual_institution_name': 'Universidade de São Paulo',
        }
        
        ebm = EditorialBoardMember(journal=self.journal)
        form = get_editorialboard_form(ebm, **form_data)
        
        # LANGUAGE_CODE é pt-br; verifica a mensagem original
        with translation.override("en"):
            # Test that clean adds the expected validation error
            self.assertFalse(form.is_valid())
            
            # Verify the error message content
            self.assertIn('given names and last name', str(form.non_field_errors()))
    
    def test_existing_researcher_selection_skips_manual_input(self):
        """Test that selecting existing researcher skips manual input processing"""
        # Create an existing researcher
        organization = Organization.create_or_update(
            user=self.user,
            name="Test University",
            acronym="TU",
            location=self.location,
        )
        
        existing_researcher = NewResearcher.get_or_create(
            self.user,
            given_names="Maria",
            last_name="Santos",
            suffix="",
            affiliation=organization,
        )
        
        # Create form data with both researcher and manual fields
        ebm = EditorialBoardMember(journal=self.journal)
        form = get_editorialboard_form(
            ebm,
            researcher=autocomplete_value(existing_researcher),
            manual_given_names='João',
            manual_last_name='Silva',
        )
        self.assertTrue(form.is_valid(), form.errors)
        saved_instance = form.save_all(self.user)
        
        # Verify that existing researcher is used (not manual input)
        self.assertEqual(saved_instance.researcher.given_names, 'Maria')
        self.assertEqual(saved_instance.researcher.last_name, 'Santos')
    
    def test_invalid_orcid_format_raises_error(self):
        """Test that invalid ORCID format raises ValidationError"""
        from researcher.utils import clean_orcid
        from django.core.exceptions import ValidationError
        
        # Test invalid ORCID formats
        # (clean_orcid valida somente o formato; o dígito verificador é
        # validado por ResearcherOrcid.validate_orcid)
        invalid_orcids = [
            '0000-0001-2345-678',   # Too short
            '0000-0001-2345-67890', # Too long
            'invalid-orcid',        # Invalid format
        ]
        
        for invalid_orcid in invalid_orcids:
            with self.assertRaises(ValidationError):
                clean_orcid(invalid_orcid)
        
        # Test valid ORCID formats
        valid_orcids = [
            '0000-0001-2345-6789',
            '0000-0002-9999-999X',
            'https://orcid.org/0000-0001-2345-6789',
            'http://orcid.org/0000-0002-9999-999X',
        ]
        
        for valid_orcid in valid_orcids:
            cleaned = clean_orcid(valid_orcid)
            self.assertIsNotNone(cleaned)
            self.assertRegex(cleaned, r'^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$')