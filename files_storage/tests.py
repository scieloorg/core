# Create your tests here.
from unittest.mock import Mock, patch

from django.test import TestCase

from files_storage.controller import FilesStorageManager


@patch("files_storage.models.MinioConfiguration.objects.get")
class FilesStorageManagerTest(TestCase):
    def setUp(self):
        self.mock_minio_storage = Mock()
        self.mock_minio_storage.host = "my_host"
        self.mock_minio_storage.access_key = "my_access_key"
        self.mock_minio_storage.secret_key = "my_secret_key"
        self.mock_minio_storage.bucket_root = "my_bucket_root"
        self.mock_minio_storage.bucket_app_subdir = "my_bucket_app_subdir"
        self.mock_minio_storage.secure = "my_secure"

    @patch("files_storage.minio.MinioStorage.fput")
    def test__push_file(
        self,
        mock_fput,
        mock_minio_config_objects_get,
    ):
        mock_minio_config_objects_get.return_value = self.mock_minio_storage

        mock_fput.return_value = "uri"

        files_storage_manager = FilesStorageManager("name")
        uri = files_storage_manager._push_file(
            source_filepath="/root/folder1/folder2/filename.xml",
            subdirs="subdir1/subdir2",
            preserve_name=True,
        )
        mock_fput.assert_called_with(
            "/root/folder1/folder2/filename.xml",
            "subdir1/subdir2/filename.xml",
        )
        self.assertEqual("uri", uri)

    @patch("files_storage.controller.MinioStorage.register")
    def test_push_file(
        self, mock_minio_storage_register, mock_minio_config_objects_get
    ):
        mock_minio_config_objects_get.return_value = self.mock_minio_storage
        mock_minio_storage_register.return_value = {
            "uri": "registered_uri",
            "object_name": "registered_object_name",
            "origin_name": "my_file_path.xxx",
        }

        files_storage_manager = FilesStorageManager("name")
        result = files_storage_manager.push_file(
            "my_file_path.xxx", "my_subdirs", preserve_name=True
        )
        mock_minio_storage_register.assert_called_with(
            "my_file_path.xxx",
            subdirs="my_bucket_app_subdir/my_subdirs",
            preserve_name=True,
        )

    @patch("files_storage.controller.MinioStorage.fput_content")
    def test_push_xml_content(
        self, mock_minio_storage_fput_content, mock_minio_config_objects_get
    ):
        mock_minio_config_objects_get.return_value = self.mock_minio_storage

        mock_minio_storage_fput_content.return_value = "registered_uri"

        files_storage_manager = FilesStorageManager("name")
        result = files_storage_manager.push_xml_content(
            filename="given_filename.xml",
            subdirs="given_subdirs/a/b",
            content="isso é um conteúdo do xml",
            finger_print="given_fingerprint",
        )
        mock_minio_storage_fput_content.assert_called_with(
            "isso é um conteúdo do xml",
            mimetype="text/xml",
            object_name=(
                "my_bucket_app_subdir/"
                "given_subdirs/a/b/"
                "given_filename/"
                "given_fingerprint/"
                "given_filename.xml"
            ),
        )
