from unittest.mock import ANY, Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from pid_provider.controller import PidProvider
from pid_provider.models import PidProviderXML

User = get_user_model()


# def get_mock_config():
#     config = object()
#     config.host = ''
#     config.access_key = ''
#     config.secret_key = ''
#     config.bucket_root = ''
#     config.bucket_app_subdir = 'bucket-app-subdir'
#     config.secure = ''
#     return config


class PidProviderTest(TestCase):
    @patch("pid_provider.models.XMLSPS.save")
    @patch("pid_provider.models.XMLVersion.save")
    @patch("pid_provider.models.XMLIssue.save")
    @patch("pid_provider.models.XMLJournal.save")
    @patch("pid_provider.models.PidProviderXML.save")
    @patch(
        "pid_provider.models.PidProviderXML._get_unique_v3",
        return_value="SJLD63mRxz9nTXtyMj7SLwk",
    )
    @patch(
        "pid_provider.models.PidProviderXML._get_unique_v2",
        return_value="S2236-89062022061645340",
    )
    @patch("pid_provider.controller.PidProviderConfig.get_or_create")
    def test_provide_pid_for_xml_zip(
        self,
        mock_pid_provider_config,
        mock_get_unique_v2,
        mock_get_unique_v3,
        mock_pid_provider_xml_save,
        mock_xml_journal_save,
        mock_xml_issue_save,
        mock_xml_version_save,
        mock_xmlsps_save,
    ):
        pid_provider = PidProvider()
        result = pid_provider.provide_pid_for_xml_zip(
            zip_xml_file_path="./pid_provider/fixtures/sub-article/2236-8906-hoehnea-49-e1082020.xml.zip",
            user=User.objects.first(),
        )
        result = list(result)
        self.assertEqual("SJLD63mRxz9nTXtyMj7SLwk", result[0]["v3"])
        self.assertEqual("S2236-89062022061645340", result[0]["v2"])
        self.assertIsNone(result[0]["aop_pid"])
        self.assertIsNotNone(result[0]["created"])
        self.assertIsNone(result[0]["updated"])
        self.assertEqual("2236-8906-hoehnea-49-e1082020.xml", result[0]["filename"])
        self.assertEqual("created", result[0]["record_status"])
        self.assertEqual(True, result[0]["xml_changed"])

    @patch("pid_provider.models.PidProviderXML._query_document")
    @patch("pid_provider.models.PidProviderXML.is_equal_to", return_value=True)
    def test_provide_pid_for_xml_with_pre_do_nothing_because_it_is_already_updated(
        self,
        mock_is_equal,
        mock_query_document,
    ):
        # dubla o registro encontrado
        pid_provider_xml = Mock(PidProviderXML)
        pid_provider_xml.data = {"v3": ""}
        mock_query_document.return_value = pid_provider_xml

        pid_provider_ = PidProvider()
        result = pid_provider_.provide_pid_for_xml_zip(
            zip_xml_file_path="./pid_provider/fixtures/sub-article/2236-8906-hoehnea-49-e1082020.xml.zip",
            user=User.objects.first(),
        )
        result = list(result)
        expected = {
            "filename": "2236-8906-hoehnea-49-e1082020.xml",
            "v3": "",
            "xml_with_pre": ANY,
        }
        self.assertDictEqual(result[0], expected)
