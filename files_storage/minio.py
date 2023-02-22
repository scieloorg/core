# coding: utf-8
import hashlib
import json
import logging
import os
import tempfile
from mimetypes import types_map
from zipfile import ZipFile, BadZipFile

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)


def get_mimetype(file_path):
    name, ext = os.path.splitext(file_path)
    return types_map.get(ext, "application/octet-stream")


class SHA1Error(Exception):
    ...


class MinioStorageFPutContentError(Exception):
    ...


class MinioStorageFPutError(Exception):
    ...


class MinioStorageGetUrlsError(Exception):
    ...


class MinioStorageRegisterError(Exception):
    ...


class MinioStorageFgetError(Exception):
    ...


class MinioStorageGetZipFileItemsError(Exception):
    ...


class MinioStorageCreateBucketError(Exception):
    ...


class MinioStorageSetPublicBucketError(Exception):
    ...


def sha1(path):
    logger.debug("Lendo arquivo: %s", path)
    _sum = hashlib.sha1()
    try:
        with open(path, "rb") as file:
            while True:
                chunk = file.read(1024)
                if not chunk:
                    break
                _sum.update(chunk)
        return _sum.hexdigest()
    except (ValueError, FileNotFoundError) as e:
        raise SHA1Error("%s: %s" % (path, e))


class MinioStorage:
    def __init__(
        self, minio_host, minio_access_key, minio_secret_key,
        bucket_root, bucket_subdir,
        minio_secure=True, minio_http_client=None,
    ):

        self.bucket_root = bucket_root
        self.POLICY_READ_ONLY = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                    "Resource": [f"arn:aws:s3:::{self.bucket_root}"],
                },
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{self.bucket_root}/*"],
                },
            ],
        }
        self.minio_host = minio_host
        self.minio_access_key = minio_access_key
        self.minio_secret_key = minio_secret_key
        self.minio_secure = minio_secure
        self.http_client = minio_http_client
        self._client_instance = None
        self.bucket_subdir = bucket_subdir

    @property
    def _client(self):
        """Posterga a instanciação de `pymongo.MongoClient` até o seu primeiro
        uso.
        """
        if not self._client_instance:
            # Initialize minioClient with an endpoint and access/secret keys.
            self._client_instance = Minio(
                self.minio_host,
                access_key=self.minio_access_key,
                secret_key=self.minio_secret_key,
                secure=self.minio_secure,
                http_client=self.http_client
            )
            logger.debug(
                "new Minio client created: <%s at %s>",
                repr(self._client_instance),
                id(self._client_instance),
            )

        logger.debug(
            "using Minio client: <%s at %s>",
            repr(self._client_instance),
            id(self._client_instance),
        )
        return self._client_instance

    def _create_bucket(self):
        try:
            # Make a bucket with the make_bucket API call.
            self._client.make_bucket(
                self.bucket_root, location=self.bucket_subdir
            )
            self._set_public_bucket()
        except Exception as e:
            raise MinioStorageCreateBucketError(
                "Unable to create bucket %s %s %s" %
                (self.bucket_root, type(e), e)
            )

    def _set_public_bucket(self):
        try:
            self._client.set_bucket_policy(
                self.bucket_root, json.dumps(self.POLICY_READ_ONLY)
            )
        except Exception as e:
            raise MinioStorageSetPublicBucketError(
                "Unable to set public bucket %s %s %s" %
                (self.bucket_root, type(e), e)
            )

    def build_object_name(self, file_path, subdirs, preserve_name):
        """
        2 niveis de Pastas onde :
            * o primeiro representando o periódico por meio do ISSN+Acrônimo
            * o segundo o scielo-id do documento no seu idioma original.
            Var: Prefix
        O nome do arquivo sera alterado para soma SHA-1, para evitar duplicatas e conflitos em nomes.
        """
        original_name, file_extension = os.path.splitext(os.path.basename(file_path))
        if preserve_name:
            n_filename = original_name
        else:
            n_filename = sha1(file_path)
        return os.path.join(subdirs, f"{n_filename}{file_extension}")

    def get_urls(self, media_path: str) -> str:
        try:
            url = self._client.presigned_get_object(
                self.bucket_root, media_path)
            return url.split("?")[0]
        except Exception as e:
            raise MinioStorageGetUrlsError(
                "Unable to get urls %s %s %s %s" %
                (self.bucket_root, media_path, type(e), e)
            )

    def register(self, file_path, subdirs="", original_uri=None, preserve_name=False) -> str:
        try:
            object_name = self.build_object_name(file_path, subdirs, preserve_name)
            metadata = {"origin_name": os.path.basename(file_path)}
            if original_uri is not None:
                metadata.update({"origin_uri": original_uri})

            logger.debug(
                "Registering %s in %s with metadata %s", file_path, object_name, metadata
            )
            uri = self.fput(file_path, object_name)

            metadata.update(
                {"object_name": object_name, "uri": uri}
            )
            return metadata
        except Exception as e:
            raise MinioStorageRegisterError(
                "Unable to register %s %s %s %s" %
                (file_path, subdirs, type(e), e)
            )

    def fput(self, file_path, object_name, mimetype=None) -> str:
        try:
            metadata = {"origin_name": os.path.basename(file_path)}
            logger.debug(
                "Registering %s in %s with metadata %s",
                file_path, object_name, metadata
            )
            try:
                self._client.fput_object(
                    self.bucket_root,
                    object_name=object_name,
                    file_path=file_path,
                    content_type=mimetype or get_mimetype(file_path),
                )

            except S3Error as err:
                logger.error(err)
                if err.code == "NoSuchBucket":
                    self._create_bucket()
                    return self.fput(file_path, object_name, mimetype)
            return self.get_urls(object_name)
        except Exception as e:
            raise MinioStorageFPutError(
                "Unable to execute fput for %s %s %s %s" %
                (file_path, object_name, type(e), e)
            )

    def fput_content(self, content, mimetype, object_name) -> str:
        try:
            tf = tempfile.NamedTemporaryFile(delete=False)
            with open(tf.name, "w") as fp:
                fp.write(content)
            return self.fput(tf.name, object_name, mimetype)
        except Exception as e:
            raise MinioStorageFPutContentError(
                "Unable to create temporary file %s %s %s" %
                (object_name, type(e), e)
            )

    def remove(self, object_name: str) -> None:
        # Remove an object.
        # https://docs.min.io/docs/python-client-api-reference.html#remove_object
        return self._client.remove_object(self.bucket_root, object_name)

    def fget(self, object_name, downloaded_file_path=None):
        """
        https://docs.min.io/docs/python-client-api-reference.html#fget_object
        """
        try:
            if not downloaded_file_path:
                tf = tempfile.NamedTemporaryFile(delete=False)
                downloaded_file_path = tf.name

            self._client.fget_object(
                self.bucket_root, object_name, downloaded_file_path)

            return downloaded_file_path
        except Exception as err:
            raise MinioStorageFgetError(
                "Unable to fget %s %s %s" %
                (object_name, type(e), e)
            )

    def get_zip_file_items(self, object_name, downloaded_folder_path=None):
        """
        Download a zipfile and returns its content as dict

        Returns
        -------
        dict
            {
                "item1": "/tmp/zip_file_item_1",
                "item2": "/tmp/zip_file_item_2",
            }
        """
        try:
            source = object_name

            zip_path = self.fget(object_name)
            source = zip_path

            with ZipFile(zip_path) as zf:
                if not downloaded_folder_path:
                    downloaded_folder_path = tempfile.TemporaryDirectory()

                files = {}
                for filename in zf.namelist():
                    file_path = os.path.join(downloaded_folder_path, filename)
                    with zf.open(filename, "rb") as fp:
                        with open(file_path, "wb") as wfp:
                            wfp.write(fp.read())
                    files[filename] = file_path
            return files
        except Exception as e:
            raise MinioStorageGetZipFileItemsError(
                "Unable to get items from %s %s %s" %
                (source, type(e), e)
            )
