from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from files_storage.controller import FilesStorageManager
from pid_provider.controller import PidProvider

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
    @patch("pid_provider.models.PidProviderXML.register")
    def test_provide_pid_for_xml_zip(self, mock_models_register):
        mock_models_register.return_value = {
            "v3": "V3",
            "v2": "V2",
            "aop_pid": "AOPPID",
            "xml_uri": "URI",
            "article": "ARTICLE",
            "created": "2020-01-02T00:00:00",
            "updated": "2020-01-02T00:00:00",
            "record_status": "created",
            "xml_changed": True,
        }

        pid_provider = PidProvider("pid-provider")
        result = pid_provider.provide_pid_for_xml_zip(
            zip_xml_file_path="./pid_provider/fixtures/sub-article/2236-8906-hoehnea-49-e1082020.xml.zip",
            user=User.objects.first(),
            synchronized=None,
        )
        result = list(result)
        self.assertEqual("V3", result[0]["v3"])
        self.assertEqual("V2", result[0]["v2"])
        self.assertEqual("AOPPID", result[0]["aop_pid"])
        self.assertEqual("URI", result[0]["xml_uri"])
        self.assertEqual("ARTICLE", result[0]["article"])
        self.assertEqual("2020-01-02T00:00:00", result[0]["created"])
        self.assertEqual("2020-01-02T00:00:00", result[0]["updated"])
        self.assertEqual("2236-8906-hoehnea-49-e1082020.xml", result[0]["filename"])
        self.assertEqual("created", result[0]["record_status"])
        self.assertEqual(True, result[0]["xml_changed"])
