from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre

from collection.models import Collection
from journal.models import Journal, OfficialJournal, SciELOJournal
from pid_provider.base_pid_provider import BasePidProvider
from pid_provider.models import PidProviderXML, XMLVersion


class ProvidePidForXMLURITests(SimpleTestCase):
    def setUp(self):
        self.provider = BasePidProvider()
        self.user = Mock(username="operator")

    @patch("pid_provider.base_pid_provider.UnexpectedEvent.create")
    @patch("pid_provider.base_pid_provider.XMLWithPre.create")
    def test_rejects_xml_with_different_pid_v3(self, create_xml, create_event):
        create_xml.return_value = [Mock(v3="xml-pid")]
        self.provider.provide_pid_for_xml_with_pre = Mock()

        result = self.provider.provide_pid_for_xml_uri(
            xml_uri="https://www.scielo.br/article.xml",
            name="scl_counter-pid",
            user=self.user,
            expected_pid_v3="counter-pid",
        )

        self.assertEqual(result["error_type"], "<class 'ValueError'>")
        self.assertIn("PID v3 mismatch", result["error_msg"])
        self.provider.provide_pid_for_xml_with_pre.assert_not_called()
        create_event.assert_called_once()
        self.assertEqual(
            create_event.call_args.kwargs["detail"]["stage"],
            "pid_v3_mismatch",
        )

    @patch("pid_provider.base_pid_provider.UnexpectedEvent.create")
    @patch("pid_provider.base_pid_provider.XMLWithPre.create")
    @patch("pid_provider.base_pid_provider.transaction.atomic")
    def test_preserves_matching_opac_pid_v3(
        self,
        atomic,
        create_xml,
        create_event,
    ):
        xml_with_pre = Mock(v3="opac-pid")
        create_xml.return_value = [xml_with_pre]
        self.provider.provide_pid_for_xml_with_pre = Mock(
            return_value={"v3": "opac-pid", "created": True}
        )

        result = self.provider.provide_pid_for_xml_uri(
            xml_uri="https://www.scielo.br/article.xml",
            name="scl_opac-pid",
            user=self.user,
            expected_pid_v3="opac-pid",
        )

        self.assertEqual(result["v3"], "opac-pid")
        atomic.assert_called_once_with()
        self.provider.provide_pid_for_xml_with_pre.assert_called_once()
        create_event.assert_not_called()

    @patch("pid_provider.base_pid_provider.UnexpectedEvent.create")
    @patch("pid_provider.base_pid_provider.XMLWithPre.create")
    def test_records_xml_download_failure(self, create_xml, create_event):
        create_xml.side_effect = OSError("unavailable")

        result = self.provider.provide_pid_for_xml_uri(
            xml_uri="https://www.scielo.br/article.xml",
            name="scl_opac-pid",
            user=self.user,
            expected_pid_v3="opac-pid",
        )

        self.assertIn("unavailable", result["error_msg"])
        create_event.assert_called_once()
        self.assertEqual(
            create_event.call_args.kwargs["detail"]["stage"],
            "xml_fetch_failed",
        )


class ProvidePidForXMLURIIntegrationTests(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.override_settings = override_settings(
            MEDIA_ROOT=self.media_directory.name
        )
        self.override_settings.enable()
        self.addCleanup(self.override_settings.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.provider = BasePidProvider()
        self.user = get_user_model().objects.create_user(username="operator")
        fixture_path = (
            Path(__file__).parents[1]
            / "fixtures"
            / "adendo"
            / "adendo_01.xml"
        )
        self.xml_content = fixture_path.read_text()
        self.pid_v3 = "s8JQvV57hfnwnMSFWS38G8S"

        # somente o XML da coleção principal é a versão atual do documento
        collection = Collection.objects.create(
            acron3="scl", network_classification=["scielonetwork"], creator=self.user
        )
        SciELOJournal.objects.create(
            journal=Journal.objects.create(
                official=OfficialJournal.objects.create(
                    issn_print="0102-4450",
                    issn_electronic="1678-460X",
                    creator=self.user,
                ),
                creator=self.user,
            ),
            collection=collection,
            journal_acron="ln",
            issn_scielo="0102-4450",
            creator=self.user,
        )

    def xml_with_pre(self, xml_content):
        xml_with_pre = list(XMLWithPre.create(xml_content=xml_content))[0]
        xml_with_pre.collection = "scl"
        return xml_with_pre

    def test_creates_and_versions_xml_while_preserving_opac_pid_v3(self):
        first_xml = self.xml_with_pre(self.xml_content)
        updated_content = self.xml_content.replace(
            "<article-title>Adendo</article-title>",
            "<article-title>Adendo atualizado</article-title>",
        )
        updated_xml = self.xml_with_pre(updated_content)

        # substitui XMLWithPre somente em base_pid_provider, preservando a
        # leitura dos arquivos das versões (XMLVersion.xml_with_pre)
        with patch("pid_provider.base_pid_provider.XMLWithPre") as mock_xml_with_pre:
            mock_xml_with_pre.create.side_effect = ([first_xml], [updated_xml])
            created = self.provider.provide_pid_for_xml_uri(
                xml_uri="https://www.scielo.br/article.xml",
                name="adendo_01",
                user=self.user,
                origin_date="2026-01-01",
                expected_pid_v3=self.pid_v3,
            )
            updated = self.provider.provide_pid_for_xml_uri(
                xml_uri="https://www.scielo.br/article.xml",
                name="adendo_01",
                user=self.user,
                origin_date="2026-02-01",
                force_update=True,
                expected_pid_v3=self.pid_v3,
            )

        record = PidProviderXML.objects.get(v3=self.pid_v3)
        self.assertEqual(created["v3"], self.pid_v3)
        self.assertEqual(updated["v3"], self.pid_v3)
        self.assertEqual(record.v3, self.pid_v3)
        self.assertEqual(
            XMLVersion.objects.filter(pid_provider_xml=record).count(),
            2,
        )
