import tempfile
from unittest.mock import patch
from datetime import date
from django.test import TestCase
from django.urls import reverse

from core.users.models import User
from organization.models import Organization
from researcher.models import NewResearcher
from .tasks import importar_csv_task_organization, importar_csv_task_newresearcher, importar_csv_task_editorialboardmember
from journal.models import Journal
from location.models import Location
from editorialboard.models import EditorialBoardMember


class ImportCSVTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username="teste", password="teste", is_superuser=True
        )
        self.journal = Journal.objects.create(title="Revista XXXX")
        self.client.force_login(self.user)
        self.location = Location.create_or_update(
            user=self.user,
            city_name="São Paulo",
            country_acronym="BR",
            country_name="Brasil",
            state_text="São Paulo",
            state_acronym="SP",
            state_name=None,
        )
        self.csv_content_organization = """organization_name;country_code;city;state;acronym;url;institution_type_mec
Organization 1;BR;São Paulo;São Paulo;ORG1;www.org1.com.br;organização sem fins de lucros"""
        self.csv_content_newresearcher = """orcid;given_names;last_name;suffix;affiliation;country_code;city;state;email
0000-0002-9147-0547;Anna;Taomeaome;Jr.;Universidade Federal de São Carlos;BR;São Paulo;SP;anna.taomeaome@ufsc.br"""
        self.csv_content_editorialboardmember = """title_journal;affiliation;country_code;city;state;orcid;given_names;last_name;suffix;std_role;declared_role;initial_year;final_year
Revista XXXX;Universidade Federal de São Carlos;BR;São Paulo;SP;0000-0002-9147-0547;Anna;Taomeaome;Jr.;editor-in-chief;editor;2020;2022"""

    @staticmethod
    def create_temp_file(content):
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".csv", mode="w+", encoding="utf-8"
        )
        temp_file.write(content)
        temp_file.seek(0)
        return temp_file

    @patch("core_settings.tasks.importar_csv_task.apply_async")
    def test_import_csv_organization_with_required_columns(self, mock_apply_async):
        mock_apply_async.return_value = None
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".csv", mode="w+", encoding="utf-8"
        )
        temp_file.write(self.csv_content_organization)
        temp_file.seek(0)
        response = self.client.post(
            reverse("import_csv"),
            {
                "csv_file": temp_file,
                "type_csv": "organization",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {
                "status": True,
                "message": "CSV importado com sucesso! Realizando importação...",
            },
        )

    @patch("core_settings.tasks.importar_csv_task.apply_async")
    def test_import_csv_organization_with_miss_required_columns(self, mock_apply_async):
        self.csv_content_organization_miss_country_code = """organization_name;city;state;acronym;url;institution_type_mec 
Organization 1;São Paulo;São Paulo;ORG1;www.org1.com.br;organização sem fins de lucros"""
        mock_apply_async.return_value = None
        temp_file = self.create_temp_file(self.csv_content_organization_miss_country_code)
        response = self.client.post(
            reverse("import_csv"),
            {
                "csv_file": temp_file,
                "type_csv": "organization",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {
                "status": False,
                "message": f"Colunas faltando. Colunas requeridas: {sorted({'organization_name', 'country_code', 'city', 'state'})}.",
            },
        )

    def test_import_csv_task_organization(self):
        temp_file = self.create_temp_file(content=self.csv_content_organization)
        importar_csv_task_organization(
            username="teste",
            tmp_path=temp_file.file.name,
        )
        organization = Organization.objects.all()
        self.assertEqual(organization.count(), 1)
        self.assertEqual(organization[0].name, "Organization 1")
        self.assertEqual(organization[0].acronym, "ORG1")
        self.assertEqual(organization[0].location.country.acronym, "BR")
        self.assertEqual(organization[0].location.city.name, "São Paulo")
        self.assertEqual(organization[0].location.state.name, "São Paulo")
        self.assertEqual(organization[0].url, "www.org1.com.br")
        self.assertEqual(
            organization[0].institution_type_mec, "organização sem fins de lucros"
        )

    def test_import_csv_task_newresearcher(self):
        temp_file = self.create_temp_file(content=self.csv_content_newresearcher)
        importar_csv_task_newresearcher(
            username="teste",
            tmp_path=temp_file.file.name,
        )
        researcher = NewResearcher.objects.all()
        self.assertEqual(researcher.count(), 1)
        self.assertEqual(researcher[0].given_names, "Anna")
        self.assertEqual(researcher[0].last_name, "Taomeaome")
        self.assertEqual(researcher[0].suffix, "Jr.")
        self.assertEqual(researcher[0].fullname, "Anna Taomeaome Jr.")
        self.assertEqual(researcher[0].researcher_ids.count(), 1)
        self.assertEqual(
            researcher[0].researcher_ids.filter(source_name="EMAIL")[0].identifier, "anna.taomeaome@ufsc.br"
        )
        self.assertEqual(
            researcher[0].orcid.orcid, "0000-0002-9147-0547"
        )

    def test_importar_csv_task_editorialboardmember(self):
        temp_file = self.create_temp_file(content=self.csv_content_editorialboardmember)
        importar_csv_task_editorialboardmember(
            username="teste",
            tmp_path=temp_file.file.name,
        )
        editorial_board_member = EditorialBoardMember.objects.all()
        self.assertEqual(editorial_board_member.count(), 1)
        self.assertEqual(editorial_board_member.first().role_editorial_board.first().role.declared_role, "editor")
        self.assertEqual(editorial_board_member.first().role_editorial_board.first().role.std_role, "editor-in-chief")
        self.assertEqual(editorial_board_member.first().role_editorial_board.first().initial_year, date(2020, 1, 1))
        self.assertEqual(editorial_board_member.first().role_editorial_board.first().final_year, date(2022, 1, 1))
        self.assertEqual(editorial_board_member.first().researcher.affiliation.name, "Universidade Federal de São Carlos")
        self.assertEqual(editorial_board_member.first().researcher.given_names, "Anna")
        self.assertEqual(editorial_board_member.first().researcher.last_name, "Taomeaome")
        self.assertEqual(editorial_board_member.first().researcher.suffix, "Jr.")
        self.assertEqual(editorial_board_member.first().researcher.orcid.orcid, "0000-0002-9147-0547")

