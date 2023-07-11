from unittest.mock import ANY, MagicMock, Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from pid_provider.controller import PidProvider
from pid_provider.models import (
    PidProviderConfig,
    PidProviderXML,
    SyncFailure,
    XMLVersion,
)
from xmlsps.xml_sps_lib import get_xml_items

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
    @patch("pid_provider.controller.xml_sps_lib.get_xml_with_pre_from_uri")
    @patch("pid_provider.controller.requests.post")
    @patch("pid_provider.models.XMLVersion.save")
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
    def test_request_pid_for_xml_zip(
        self,
        mock_pid_provider_config,
        mock_get_unique_v2,
        mock_get_unique_v3,
        mock_pid_provider_xml_save,
        mock_xml_version_create,
        mock_post,
        mock_get_xml_with_pre_from_uri,
    ):
        pid_provider_response = {
            "v3": "SJLD63mRxz9nTXtyMj7SLwk",
            "v2": "S2236-89062022061645340",
            "aop_pid": "AOPPID",
            "xml_uri": "xml_uri",
            "created": "2020-01-02T00:00:00",
            "updated": "2020-01-02T00:00:00",
            "record_status": "created",
            "xml_changed": True,
        }
        # dubla a configuração de pid provider
        mock_pid_provider_config.return_value = MagicMock(PidProviderConfig)
        # dubla a função que retorna a árvore de XML a partir de um URI
        xml_items = get_xml_items(
            "./pid_provider/fixtures/sub-article/2236-8906-hoehnea-49-e1082020.xml"
        )
        mock_get_xml_with_pre_from_uri.return_value = xml_items[0]["xml_with_pre"]

        # dubla resposta da requisição do token
        mock_get_token_response = Mock()
        mock_get_token_response.json = Mock()
        mock_get_token_response.json.return_value = {
            "refresh": "eyJhbGciO...",
            "access": "eyJ0b2tlb...",
        }
        # dubla resposta da requisição do PID v3
        mock_post_xml_response = Mock()
        mock_post_xml_response.json = Mock()
        mock_post_xml_response.json.return_value = [pid_provider_response]

        mock_post.side_effect = [
            mock_get_token_response,
            mock_post_xml_response,
        ]

        pid_provider = PidProvider()
        result = pid_provider.request_pid_for_xml_zip(
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

    @patch("pid_provider.models.XMLVersion.save")
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
    def test_request_pid_for_xml_zip_was_unable_to_get_pid_from_core(
        self,
        mock_pid_provider_config,
        mock_get_unique_v2,
        mock_get_unique_v3,
        mock_pid_provider_xml_save,
        mock_xml_version_create,
    ):
        # dubla a configuração de pid provider
        mock_pid_provider_config.return_value = None
        mock_pid_provider_xml_save.return_value = None
        mock_xml_version_create.return_value = XMLVersion()

        pid_provider_ = PidProvider()
        result = pid_provider_.request_pid_for_xml_zip(
            zip_xml_file_path="./pid_provider/fixtures/sub-article/2236-8906-hoehnea-49-e1082020.xml.zip",
            user=User.objects.first(),
        )
        result = list(result)

        self.assertEqual("SJLD63mRxz9nTXtyMj7SLwk", result[0]["v3"])
        self.assertEqual("S2236-89062022061645340", result[0]["v2"])
        self.assertIsNone(result[0]["aop_pid"])
        self.assertEqual("2236-8906-hoehnea-49-e1082020.xml", result[0]["filename"])
        self.assertEqual("created", result[0]["record_status"])
        self.assertEqual(True, result[0]["xml_changed"])
        self.assertEqual(False, result[0]["synchronized"])

    def test_request_pid_for_xml_with_pre_returns_error_type_because_of_bad_xml(
        self,
    ):
        pid_provider_ = PidProvider()
        result = pid_provider_.request_pid_for_xml_zip(
            zip_xml_file_path="./pid_provider/fixtures/incomplete/incomplete.xml.zip",
            user=User.objects.first(),
        )
        result = list(result)
        self.assertIsNotNone(result[0]["error_type"])

    @patch("pid_provider.models.PidProviderXML._query_document")
    @patch("pid_provider.models.PidProviderXML.is_equal_to", return_value=True)
    def test_request_pid_for_xml_with_pre_do_nothing_because_it_is_already_updated(
        self,
        mock_is_equal,
        mock_query_document,
    ):
        # dubla o registro encontrado
        pid_provider_xml = Mock(PidProviderXML)
        pid_provider_xml.synchronized = True
        pid_provider_xml.data = {"v3": ""}
        mock_query_document.return_value = pid_provider_xml

        pid_provider_ = PidProvider()
        result = pid_provider_.request_pid_for_xml_zip(
            zip_xml_file_path="./pid_provider/fixtures/sub-article/2236-8906-hoehnea-49-e1082020.xml.zip",
            user=User.objects.first(),
        )
        result = list(result)
        self.assertDictEqual(
            result[0], {"filename": "2236-8906-hoehnea-49-e1082020.xml", "v3": ""}
        )
