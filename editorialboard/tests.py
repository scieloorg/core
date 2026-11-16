import hashlib
import json
from datetime import date
from unittest.mock import patch

from curl_cffi.requests.exceptions import ConnectionError, HTTPError, Timeout
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.utils import translation
from wagtail.admin.panels import get_edit_handler
from wagtail.documents.models import Document

from collection.models import Collection
from core.models import Gender
from editorialboard import choices
from editorialboard.models import (
    EditorialBoardHTML,
    EditorialBoardMember,
    EditorialBoardMemberFile,
)
from editorialboard.sources.classic_website import extract_edboard_section
from editorialboard.sources.editors_anchor import extract_editors_anchor_section
from editorialboard.tasks import (
    collect_editorial_board_html,
    fetch_editorial_board_html,
    get_scielo_journals_queryset,
)
from editorialboard.views import import_file_ebm
from journal.models import Journal, SciELOJournal
from location.models import Location
from organization.models import Organization
from researcher.models import NewResearcher, ResearcherIds, ResearcherOrcid

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
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware

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

        member = EditorialBoardMember.objects.first()
        member_researcher = member.researcher

        self.assertEqual(member_researcher.fullname, "John Doe Jr")
        self.assertEqual(member_researcher.affiliation.name, "Institution")
        self.assertEqual(member_researcher.orcid.orcid, "0000-0000-0000-0001")
        self.assertEqual(member.journal.title, "Revista XXXX")

        member_role_editorial_board = member.role_editorial_board.first()
        self.assertEqual(member_role_editorial_board.role.declared_role, "Editor")
        self.assertEqual(member_role_editorial_board.initial_year, date(2020, 1, 1))
        self.assertEqual(member_role_editorial_board.final_year, date(2020, 1, 1))


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
        
        # Verify affiliation was created
        self.assertIsNotNone(saved_instance.researcher.affiliation)
        self.assertEqual(saved_instance.researcher.affiliation.name, 'Universidade de São Paulo')

        # Verify ORCID was created and linked
        self.assertIsNotNone(saved_instance.researcher.orcid)
        self.assertEqual(saved_instance.researcher.orcid.orcid, '0000-0001-2345-6789')

        # Verify Lattes ID was created and linked
        lattes_ids = ResearcherIds.objects.filter(
            researcher=saved_instance.researcher,
            source_name='LATTES'
        )
        self.assertEqual(
            list(lattes_ids.values_list('identifier', flat=True)), ['1234567890123456']
        )

        # Verify Email was created and linked
        email_ids = ResearcherIds.objects.filter(
            researcher=saved_instance.researcher,
            source_name='EMAIL'
        )
        self.assertEqual(
            list(email_ids.values_list('identifier', flat=True)), ['joao.silva@usp.br']
        )
    
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
        from django.core.exceptions import ValidationError

        from researcher.utils import clean_orcid

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


HEADER = """
<table><tr>
  <td><a href="/scielo.php?script=sci_serial"><img src="/img/revistas/av/plogo.gif"></a>
    <p class="issn">ISSN 2448-6132 versión impresa</p></td>
  <td><p class="titulo">CUERPO EDITORIAL</p>
    <ul><li><a href="#Editor">Comité editorial</a></li></ul></td>
</tr></table>
"""
BOARD = """
<p class="subtitulo"><a name="Editor">Comité editorial</a></p>
<table><tr><td><ul><li>Sergio Martinez, Universidad Autónoma de Nayarit</li></ul></td></tr></table>
"""
NAV = """
<p align="center">[<a href="/scielo.php?script=sci_serial">Home</a>]
  [<a href="eaboutj.htm">Acerca de esta revista</a>]</p>
"""
FOOTER = "<hr><p>© 2016 Calle Tezontle 171, México</p><script>track()</script>"
STANDARD_PAGE = (
    f"<html><head><title>Cuerpo editorial</title></head>"
    f"<body>{HEADER}{BOARD}{NAV}{FOOTER}</body></html>"
)


class ExtractEdboardSectionTest(TestCase):
    def assertOnlyBoard(self, section):
        self.assertIn("Sergio Martinez", section)
        self.assertIn("Comité editorial", section)
        for outside in ("ISSN", "CUERPO EDITORIAL", "Acerca de esta revista", "Tezontle", "track()"):
            self.assertNotIn(outside, section)

    def test_standard_page(self):
        self.assertOnlyBoard(extract_edboard_section(STANDARD_PAGE))

    def test_hr_and_nav_links_before_board_are_ignored(self):
        page = f"<html><body><hr>{NAV}{HEADER}<hr>{BOARD}{NAV}{FOOTER}</body></html>"
        self.assertOnlyBoard(extract_edboard_section(page))

    def test_nav_nested_inside_board_table(self):
        page = (
            f"<html><body>{HEADER}<table><tr><td>Sergio Martinez</td></tr>"
            f"<tr><td>Comité editorial</td></tr>{NAV}</table>{FOOTER}</body></html>"
        )
        self.assertOnlyBoard(extract_edboard_section(page))

    def test_board_wrapped_in_div(self):
        page = f"<html><body><div class='Section1'>{HEADER}{BOARD}{NAV}{FOOTER}</div></body></html>"
        self.assertOnlyBoard(extract_edboard_section(page))

    def test_concatenated_html_documents(self):
        page = (
            "<html><head><title>Cuerpo editorial</title></head></html>"
            f"<html><head></head><body>{HEADER}{BOARD}{NAV}{FOOTER}</body></html>"
        )
        self.assertOnlyBoard(extract_edboard_section(page))

    def test_without_header_starts_at_body(self):
        page = f"<html><body>{BOARD}{NAV}{FOOTER}</body></html>"
        self.assertOnlyBoard(extract_edboard_section(page))

    def test_hr_is_footer_when_nav_links_are_missing(self):
        page = f"<html><body>{HEADER}{BOARD}{FOOTER}</body></html>"
        self.assertOnlyBoard(extract_edboard_section(page))

    def test_unavailable_page_keeps_message(self):
        page = (
            f"<html><body>{HEADER}<p>Información aún no disponible.</p>"
            '<p>[<a href="javascript:history.back()">Volver</a>]</p><hr></body></html>'
        )
        section = extract_edboard_section(page)

        self.assertIn("Información aún no disponible", section)
        self.assertNotIn("Volver", section)

    def test_returns_none_without_content(self):
        self.assertIsNone(extract_edboard_section(f"<html><body>{HEADER}{NAV}</body></html>"))
        self.assertIsNone(extract_edboard_section("<!-- -->"))


EDITORS_PAGE = """
<html><body>
<nav><a href="/journal/rsp/about/#editors">Editorial Board</a>
<p>ISSN 0034-8910</p></nav>
<h1>ABOUT THE JOURNAL</h1>
<p>Focus and scope of the journal.</p>
<hr>
<p><a name="editors"></a></p>
<h1>EDITORIAL BOARD</h1>
<p><strong>Editors-in-chief</strong></p>
<table><tr><td></td><td>
<ul><li>Carlos Augusto Monteiro, Universidade de São Paulo</li></ul>
</td></tr></table>
<p>Marilia Sá Carvalho, Fundação Oswaldo Cruz</p>
<p>• Marcia Pinheiro Margis, Universidade Federal do Rio Grande do Sul</p>
<hr>
<p><a name="instructions"></a></p>
<h1>INSTRUCTIONS TO AUTHORS</h1>
<p>Submit the manuscript.</p>
<section class="journalContacts"><p>Faculdade de Saúde Pública</p></section>
</body></html>
"""


class ExtractEditorsAnchorSectionTest(TestCase):
    def test_cuts_at_the_editors_anchor(self):
        section = extract_editors_anchor_section(EDITORS_PAGE)

        self.assertIn("Carlos Augusto Monteiro", section)
        self.assertIn("Editors-in-chief", section)
        self.assertNotIn("EDITORIAL BOARD", section)
        self.assertIn("Marilia Sá Carvalho", section)
        self.assertIn("Marcia Pinheiro Margis", section)
        self.assertNotIn("ISSN", section)
        self.assertNotIn("Focus and scope", section)
        self.assertNotIn("Submit the manuscript", section)
        self.assertNotIn("Faculdade de Saúde Pública", section)

    def test_id_on_the_heading_drops_the_title(self):
        page = """
        <html><body>
        <p>ISSN 0034-8910</p>
        <h1 id="editors">EDITORIAL BOARD</h1>
        <p><strong>Editor-in-Chief</strong></p>
        <ul><li>Alex Branco Fraga, Universidade Federal do Rio Grande do Sul</li></ul>
        <h1>INSTRUCTIONS TO AUTHORS</h1>
        <p>Submit the manuscript.</p>
        </body></html>
        """
        section = extract_editors_anchor_section(page)

        self.assertNotIn("EDITORIAL BOARD", section)
        self.assertIn("Alex Branco Fraga", section)
        self.assertNotIn("Submit the manuscript", section)
        self.assertNotIn("ISSN", section)

    def test_returns_none_without_the_anchor(self):
        self.assertIsNone(extract_editors_anchor_section(STANDARD_PAGE))


def edboard_url(prefix, scheme="https"):
    return f"{scheme}://www.scielo.org.ar/revistas/aaba/{prefix}edboard.htm"


class FakeResponse:
    def __init__(self, url, status_code=200, content=b""):
        self.url = url
        self.status_code = status_code
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError(f"HTTP Error {self.status_code}", 0, self)


class FakeSession:
    """
    responses: {prefixo do idioma ou URL: valor}
    valor: bytes (200), int (status), exceção ou FakeResponse; ausente = 404
    """

    def __init__(self, responses):
        self.responses = responses
        self.calls = []
        self.cookies = type("FakeCookies", (), {"jar": [], "set": lambda *args, **kwargs: None})()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        pass

    def get(self, url):
        self.calls.append(url)
        prefix = url.rsplit("/", 1)[-1].replace("edboard.htm", "")
        value = self.responses.get(url, self.responses.get(prefix, 404))
        if isinstance(value, list):
            value = value.pop(0)
        if isinstance(value, Exception):
            raise value
        if isinstance(value, FakeResponse):
            return value
        if isinstance(value, int):
            return FakeResponse(url, status_code=value)
        return FakeResponse(url, content=value)

    def post(self, url, data=None, headers=None, allow_redirects=True):
        self.calls.append(url)
        return FakeResponse(url, status_code=200)


class EditorialBoardHTMLCollectTest(TestCase):
    def setUp(self):
        self.collection = Collection.objects.create(
            acron3="arg", domain="www.scielo.org.ar", is_active=True
        )
        self.journal = Journal.objects.create(title="Revista XXXX")
        self.scielo_journal = SciELOJournal.objects.create(
            collection=self.collection,
            journal=self.journal,
            journal_acron="aaba",
        )

    def collect(self, responses):
        session = FakeSession(responses)
        with patch(
            "editorialboard.sources.classic_website.curl_requests.Session",
            return_value=session,
        ):
            fetch_editorial_board_html(scielo_journal_id=self.scielo_journal.id)
        return session

    def test_collect_dispatches_one_task_per_journal(self):
        other = SciELOJournal.objects.create(
            collection=self.collection, journal=self.journal, journal_acron="bbbb"
        )
        with patch("editorialboard.tasks.group") as mocked_group:
            collect_editorial_board_html()

        signatures = list(mocked_group.call_args.args[0])
        self.assertEqual(
            {self.scielo_journal.id, other.id},
            {signature.kwargs["scielo_journal_id"] for signature in signatures},
        )
        mocked_group.return_value.apply_async.assert_called_once()

    def get(self, language):
        return EditorialBoardHTML.objects.get(
            scielo_journal=self.scielo_journal, language=language
        )

    def test_bunny_challenge_is_replaced_by_the_page(self):
        challenge = b'<html><body data-pow="user#ch#1#sig">Hold tight</body></html>'
        page = b"<html>Comite</html>"
        with patch(
            "core.utils.bunny_shield.solve",
            return_value="user#ch#1#sig#0",
        ):
            session = self.collect(
                {
                    edboard_url("e"): [
                        FakeResponse(edboard_url("e"), 403, challenge),
                        FakeResponse(edboard_url("e"), 200, page),
                    ]
                }
            )

        self.assertIn(
            "https://www.scielo.org.ar/.bunny-shield/verify-pow", session.calls
        )
        obj = self.get("es")
        self.assertEqual(choices.EDBOARD_FETCH_STATUS_OK, obj.status)
        self.assertEqual("<html>Comite</html>", obj.raw_html)

    def test_all_languages_are_collected(self):
        session = self.collect(
            {"e": b"<html>Comite</html>", "p": b"<html>Comite pt</html>", "i": b"<html>Board</html>"}
        )

        self.assertEqual([edboard_url("e"), edboard_url("p"), edboard_url("i")], session.calls)
        self.assertEqual(3, EditorialBoardHTML.objects.count())
        for language, raw_html in (
            ("es", "<html>Comite</html>"),
            ("pt", "<html>Comite pt</html>"),
            ("en", "<html>Board</html>"),
        ):
            obj = self.get(language)
            self.assertEqual(choices.EDBOARD_FETCH_STATUS_OK, obj.status)
            self.assertEqual(raw_html, obj.raw_html)
            self.assertIsNone(obj.detail)

    def test_edboard_section_is_saved(self):
        self.collect({"e": STANDARD_PAGE.encode("utf-8")})

        obj = self.get("es")
        self.assertIn("Sergio Martinez", obj.edboard_html)
        self.assertNotIn("ISSN", obj.edboard_html)
        self.assertNotIn("Calle Tezontle", obj.edboard_html)

    def test_editors_anchor_section_is_saved_when_requested(self):
        session = FakeSession({"e": EDITORS_PAGE.encode("utf-8")})
        with patch(
            "editorialboard.sources.classic_website.curl_requests.Session",
            return_value=session,
        ):
            fetch_editorial_board_html(
                scielo_journal_id=self.scielo_journal.id,
                editors_anchor=True,
            )

        obj = self.get("es")
        self.assertIn("Carlos Augusto Monteiro", obj.edboard_html)
        self.assertNotIn("Focus and scope", obj.edboard_html)
        self.assertNotIn("Submit the manuscript", obj.edboard_html)

    def test_classic_extraction_is_kept_without_the_flag(self):
        session = FakeSession({"e": EDITORS_PAGE.encode("utf-8")})
        with patch(
            "editorialboard.sources.classic_website.curl_requests.Session",
            return_value=session,
        ):
            fetch_editorial_board_html(scielo_journal_id=self.scielo_journal.id)

        obj = self.get("es")
        self.assertIn("Focus and scope", obj.edboard_html)
        self.assertNotIn("Carlos Augusto Monteiro", obj.edboard_html)

    def test_missing_language_does_not_affect_others(self):
        self.collect({"p": b"<html>Corpo editorial</html>"})

        self.assertEqual(choices.EDBOARD_FETCH_STATUS_OK, self.get("pt").status)
        self.assertEqual(edboard_url("p"), self.get("pt").source_url)
        for language in ("es", "en"):
            obj = self.get(language)
            self.assertEqual(choices.EDBOARD_FETCH_STATUS_NOT_FOUND, obj.status)
            self.assertEqual(404, obj.http_status)
            self.assertIsNone(obj.raw_html)

    def test_status_is_computed_per_language(self):
        self.collect({"e": 403, "p": b"   ", "i": b"<html>Board</html>"})

        self.assertEqual(choices.EDBOARD_FETCH_STATUS_ERROR, self.get("es").status)
        self.assertEqual(403, self.get("es").http_status)
        self.assertEqual(edboard_url("e"), self.get("es").source_url)
        self.assertEqual(choices.EDBOARD_FETCH_STATUS_ERROR, self.get("pt").status)
        self.assertEqual(200, self.get("pt").http_status)
        self.assertEqual(choices.EDBOARD_FETCH_STATUS_OK, self.get("en").status)

    def test_all_languages_not_found(self):
        session = self.collect({})

        self.assertEqual(3, len(session.calls))
        self.assertEqual(
            {choices.EDBOARD_FETCH_STATUS_NOT_FOUND},
            set(EditorialBoardHTML.objects.values_list("status", flat=True)),
        )

    def test_error_status_when_not_404(self):
        self.collect({"e": 500})

        self.assertEqual(choices.EDBOARD_FETCH_STATUS_ERROR, self.get("es").status)
        self.assertEqual(500, self.get("es").http_status)
        self.assertEqual(edboard_url("e"), self.get("es").source_url)
        self.assertEqual(choices.EDBOARD_FETCH_STATUS_NOT_FOUND, self.get("pt").status)

    def test_http_is_kept_for_next_languages(self):
        session = self.collect(
            {
                edboard_url("e"): ConnectionError("SSL handshake failed"),
                edboard_url("e", "http"): 404,
                edboard_url("p", "http"): b"<html>Corpo editorial</html>",
            }
        )

        self.assertEqual(
            [
                edboard_url("e"),
                edboard_url("e", "http"),
                edboard_url("p", "http"),
                edboard_url("i", "http"),
            ],
            session.calls,
        )
        self.assertEqual(edboard_url("e", "http"), self.get("es").source_url)
        self.assertEqual(404, self.get("es").http_status)
        self.assertEqual(edboard_url("p", "http"), self.get("pt").source_url)

    def test_timeout_does_not_switch_protocol(self):
        session = self.collect({"e": Timeout("timed out"), "p": b"<html>pt</html>"})

        self.assertEqual([edboard_url("e"), edboard_url("p"), edboard_url("i")], session.calls)
        self.assertEqual(choices.EDBOARD_FETCH_STATUS_ERROR, self.get("es").status)
        self.assertIsNone(self.get("es").http_status)
        self.assertEqual(edboard_url("e"), self.get("es").source_url)
        self.assertEqual(choices.EDBOARD_FETCH_STATUS_OK, self.get("pt").status)

    def test_source_url_follows_redirect(self):
        self.collect(
            {"e": FakeResponse(edboard_url("e", "http"), content=b"<html>es</html>")}
        )

        self.assertEqual(edboard_url("e", "http"), self.get("es").source_url)

    def test_connection_error_on_all_protocols(self):
        self.collect({"e": ConnectionError("refused"), "p": b"<html>pt</html>"})

        obj = self.get("es")
        self.assertEqual(choices.EDBOARD_FETCH_STATUS_ERROR, obj.status)
        self.assertIsNone(obj.http_status)
        self.assertEqual(edboard_url("e"), obj.source_url)
        self.assertIsNone(obj.detail)
        self.assertEqual(choices.EDBOARD_FETCH_STATUS_OK, self.get("pt").status)

    def test_decode_latin1_html(self):
        content = "<html><meta charset='iso-8859-1'>Comité</html>".encode("latin-1")
        self.collect({"e": content})

        self.assertIn("Comité", self.get("es").raw_html)

    def test_decode_utf8_html(self):
        self.collect({"e": "<html>Comitê</html>".encode("utf-8")})

        self.assertEqual("<html>Comitê</html>", self.get("es").raw_html)

    def test_nul_bytes_are_stripped_before_save(self):
        self.collect({"e": b"<html>Board\x00</html>"})

        obj = self.get("es")
        self.assertEqual("<html>Board</html>", obj.raw_html)
        self.assertNotIn("\x00", obj.raw_html)
        self.assertEqual(
            hashlib.sha256(b"<html>Board</html>").hexdigest(),
            obj.content_hash,
        )

    def test_same_hash_does_not_rewrite_raw_html(self):
        self.collect({"e": b"<html>Board</html>"})
        obj = self.get("es")
        first_fetched_at = obj.fetched_at
        first_hash = obj.content_hash

        self.collect({"e": b"<html>Board</html>"})

        obj.refresh_from_db()
        self.assertEqual(3, EditorialBoardHTML.objects.count())
        self.assertEqual(first_hash, obj.content_hash)
        self.assertEqual("<html>Board</html>", obj.raw_html)
        self.assertGreater(obj.fetched_at, first_fetched_at)

    def test_new_content_updates_raw_html(self):
        self.collect({"e": b"<html>Board</html>"})
        self.collect({"e": b"<html>New board</html>"})

        obj = self.get("es")
        self.assertEqual("<html>New board</html>", obj.raw_html)
        self.assertEqual(
            hashlib.sha256(b"<html>New board</html>").hexdigest(),
            obj.content_hash,
        )

    def test_failure_keeps_previous_raw_html(self):
        self.collect({"e": b"<html>Board</html>"})
        self.collect({})

        obj = self.get("es")
        self.assertEqual(choices.EDBOARD_FETCH_STATUS_NOT_FOUND, obj.status)
        self.assertEqual("<html>Board</html>", obj.raw_html)


class EditorialBoardHTMLQuerysetTest(TestCase):
    def setUp(self):
        self.journal = Journal.objects.create(title="Revista XXXX")
        self.items = {}
        for acron3 in ("arg", "mex", "scl"):
            collection = Collection.objects.create(
                acron3=acron3, domain=f"www.{acron3}.org", is_active=True
            )
            self.items[acron3] = SciELOJournal.objects.create(
                collection=collection, journal=self.journal, journal_acron="aaba"
            )

    def acrons(self, **kwargs):
        return set(
            get_scielo_journals_queryset(**kwargs).values_list(
                "collection__acron3", flat=True
            )
        )

    def test_exclude_collections(self):
        self.assertEqual(
            {"mex"}, self.acrons(exclude_collection_acron_list=["arg", "scl"])
        )

    def test_exclude_collections_as_string(self):
        self.assertEqual(
            {"arg"}, self.acrons(exclude_collection_acron_list=["mex", "scl"])
        )

    def test_include_and_exclude_collections(self):
        self.assertEqual(
            {"arg"},
            self.acrons(
                collection_acron_list=["arg", "mex"],
                exclude_collection_acron_list=["mex"],
            ),
        )

    def test_only_missing(self):
        for language, _label in choices.EDBOARD_LANGUAGES_HTML_CLASSIC_WEBSITE:
            EditorialBoardHTML.objects.create(
                scielo_journal=self.items["arg"],
                language=language,
                status=choices.EDBOARD_FETCH_STATUS_OK,
            )
        EditorialBoardHTML.objects.create(
            scielo_journal=self.items["mex"],
            language="es",
            status=choices.EDBOARD_FETCH_STATUS_OK,
        )
        EditorialBoardHTML.objects.create(
            scielo_journal=self.items["mex"],
            language="pt",
            status=choices.EDBOARD_FETCH_STATUS_NOT_FOUND,
        )
        self.assertEqual({"mex", "scl"}, self.acrons(only_missing=True))

    def test_ignores_collections_without_domain(self):
        Collection.objects.filter(acron3="mex").update(domain=None)
        Collection.objects.filter(acron3="scl").update(domain="")
        self.assertEqual({"arg"}, self.acrons())

    def test_ignores_journals_without_acronym(self):
        self.items["scl"].journal_acron = ""
        self.items["scl"].save()
        self.assertEqual({"arg", "mex"}, self.acrons())

    def test_editors_anchor_flag_follows_the_collection_list(self):
        with patch("editorialboard.tasks.group") as mocked_group:
            collect_editorial_board_html(editors_anchor_collection_acron_list=["scl"])

        flags = {
            signature.kwargs["scielo_journal_id"]: signature.kwargs["editors_anchor"]
            for signature in mocked_group.call_args.args[0]
        }
        self.assertTrue(flags[self.items["scl"].id])
        self.assertFalse(flags[self.items["mex"].id])
        self.assertFalse(flags[self.items["arg"].id])
        mocked_group.return_value.apply_async.assert_called_once()