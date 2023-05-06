# Create your tests here.
import json
from unittest.mock import Mock, patch

from django.test import TestCase
from minio.error import S3Error

from files_storage.minio import MinioStorage, MinioStorageNoSuchBucketError


class MinioStorageTest(TestCase):
    def setUp(self):
        self.minio_storage = MinioStorage(
            minio_host="localhost",
            minio_access_key="minio_access_key",
            minio_secret_key="minio_secret_key",
            bucket_root="instance_name",
            bucket_subdir="app_name",
            minio_secure=True,
            minio_http_client=None,
        )

    @patch("files_storage.minio.Minio")
    def test__client(self, mock_minio):
        client = self.minio_storage._client
        mock_minio.assert_called_with(
            "localhost",
            access_key="minio_access_key",
            secret_key="minio_secret_key",
            secure=True,
            http_client=None,
        )

    @patch("files_storage.minio.Minio.make_bucket")
    def test__create_bucket(self, mock_make_bucket):
        self.minio_storage._create_bucket()
        mock_make_bucket.assert_called_with(
            "instance_name",
            location="app_name",
        )

    @patch("files_storage.minio.Minio.set_bucket_policy")
    def test__set_bucket_policy(self, mock_set_bucket_policy):
        self.minio_storage._set_bucket_policy()
        mock_set_bucket_policy.assert_called_with(
            "instance_name",
            json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                            "Resource": ["arn:aws:s3:::instance_name"],
                        },
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject"],
                            "Resource": ["arn:aws:s3:::instance_name/*"],
                        },
                    ],
                }
            ),
        )

    def test_build_object_name(self):
        result = self.minio_storage.build_object_name(
            "/root/folder1/folder2/filename.xml",
            subdirs="subdir1/subdir2",
            preserve_name=True,
        )
        self.assertEqual("subdir1/subdir2/filename.xml", result)

    @patch("files_storage.minio.sha1", return_value="gerado_por_sha1")
    def test_build_object_name(self, mock_sha1):
        result = self.minio_storage.build_object_name(
            "/root/folder1/folder2/filename.xml",
            subdirs="subdir1/subdir2",
            preserve_name=False,
        )
        self.assertEqual("subdir1/subdir2/gerado_por_sha1.xml", result)

    @patch("files_storage.minio.Minio.presigned_get_object")
    def test_get_uri(self, mock_presigned_get_object):
        uri = self.minio_storage.get_uri("app_name")
        mock_presigned_get_object.assert_called_with(
            "instance_name",
            "app_name",
        )

    @patch("files_storage.minio.MinioStorage.fput")
    def test_register(self, mock_fput):
        metadata = self.minio_storage.register(
            file_path="/root/folder1/folder2/filename.xml",
            subdirs="subdir1/subdir2",
            preserve_name=True,
        )
        mock_fput.assert_called_with(
            "/root/folder1/folder2/filename.xml",
            "subdir1/subdir2/filename.xml",
        )

    @patch("files_storage.minio.MinioStorage.get_uri")
    @patch("files_storage.minio.Minio.fput_object")
    def test__fput_object(self, mock_client_fput_object, mock_get_uri):
        uri = self.minio_storage._fput_object(
            "/root/folder1/folder2/filename.xml",
            "subdir1/subdir2/filename.xml",
            mimetype="mimetype_informado",
        )
        mock_client_fput_object.assert_called_with(
            "instance_name",
            object_name="subdir1/subdir2/filename.xml",
            file_path="/root/folder1/folder2/filename.xml",
            content_type="mimetype_informado",
        )
        mock_get_uri.assert_called_with(
            "subdir1/subdir2/filename.xml",
        )

    @patch("files_storage.minio.MinioStorage.get_uri")
    @patch("files_storage.minio.Minio.fput_object")
    def test__fput_object_raises_exception(
        self,
        mock_client_fput_object,
        mock_get_uri,
    ):
        mock_client_fput_object.side_effect = S3Error(
            "NoSuchBucket",
            "NoSuchBucket",
            "resource",
            "request_id",
            "host_id",
            "response",
        )

        with self.assertRaises(MinioStorageNoSuchBucketError):
            uri = self.minio_storage._fput_object(
                "/root/folder1/folder2/filename.xml",
                "subdir1/subdir2/filename.xml",
                mimetype="mimetype_informado",
            )
        mock_client_fput_object.assert_called_with(
            "instance_name",
            object_name="subdir1/subdir2/filename.xml",
            file_path="/root/folder1/folder2/filename.xml",
            content_type="mimetype_informado",
        )
        mock_get_uri.assert_not_called()

    @patch("files_storage.minio.get_mimetype")
    @patch("files_storage.minio.MinioStorage._fput_object")
    def test_fput(self, mock_fput_object, mock_get_mimetype):
        mock_get_mimetype.return_value = "mimetype_identificado"

        uri = self.minio_storage.fput(
            "/root/folder1/folder2/filename.xml",
            "subdir1/subdir2/filename.xml",
            mimetype=None,
        )
        mock_fput_object.assert_called_with(
            file_path="/root/folder1/folder2/filename.xml",
            object_name="subdir1/subdir2/filename.xml",
            mimetype="mimetype_identificado",
        )
        mock_get_mimetype.assert_called_with(
            "/root/folder1/folder2/filename.xml",
        )

    @patch("files_storage.minio.MinioStorage._set_bucket_policy")
    @patch("files_storage.minio.MinioStorage._create_bucket")
    @patch("files_storage.minio.MinioStorage._fput_object")
    @patch("files_storage.minio.get_mimetype")
    def test_fput_no_such_bucket(
        self,
        mock_get_mimetype,
        mock_fput_object,
        mock_create_bucket,
        mock_set_bucket_policy,
    ):
        mock_get_mimetype.return_value = "mimetype_identificado"
        mock_fput_object.side_effect = [MinioStorageNoSuchBucketError(), "URI"]

        uri = self.minio_storage.fput(
            "/root/folder1/folder2/filename.xml",
            "subdir1/subdir2/filename.xml",
            mimetype=None,
        )
        mock_fput_object.assert_called_with(
            file_path="/root/folder1/folder2/filename.xml",
            object_name="subdir1/subdir2/filename.xml",
            mimetype="mimetype_identificado",
        )
        mock_get_mimetype.assert_called_with(
            "/root/folder1/folder2/filename.xml",
        )
        mock_create_bucket.assert_called_once_with()
        mock_set_bucket_policy.assert_called_once_with()
        self.assertEqual("URI", uri)

    @patch("files_storage.minio.Minio.remove_object")
    def test_remove(self, mock_remove):
        uri = self.minio_storage.remove("bucket_name")
        mock_remove.assert_called_with(
            "instance_name",
            "bucket_name",
        )

    @patch("files_storage.minio.MinioStorage._fput_object")
    def test_fput_content(self, mock_fput_object):
        mock_fput_object.return_value = "uri"
        uri = self.minio_storage.fput_content(
            content="<article/>",
            mimetype="text/xml",
            object_name="object_name",
        )
        self.assertEqual("uri", uri)

    @patch("files_storage.minio.MinioStorage._create_tmp_file")
    @patch("files_storage.minio.MinioStorage._fput_object")
    def test_fput_content_calls_fput_object(
        self, mock_fput_object, mock_create_tmp_file
    ):
        mock_create_tmp_file.return_value = "/tmp/file.xml"
        uri = self.minio_storage.fput_content(
            content="<article/>",
            mimetype="text/xml",
            object_name="object_name",
        )
        mock_fput_object.assert_called_with(
            file_path="/tmp/file.xml",
            object_name="object_name",
            mimetype="text/xml",
        )
