import logging
import os

from django.utils.translation import gettext_lazy as _

from files_storage import exceptions
from files_storage.minio import (
    MinioStorage,
    MinioStorageFPutContentError,
    MinioStorageRegisterError,
)
from files_storage.models import MinioConfiguration, MinioFile
from files_storage.utils import generate_finger_print


class FilesStorageManager:
    def __init__(self, files_storage_name):
        self.files_storage_name = files_storage_name

    @property
    def config(self):
        if not hasattr(self, '_config') or not self._config:
            try:
                self._config = MinioConfiguration.get_or_create(
                    name=self.files_storage_name)
            except Exception as e:
                raise exceptions.GetFilesStorageError(
                    _("Unable to get MinioStorage {} {} {}").format(
                        self.config, type(e), e
                    )
                )
        return self._config

    @property
    def files_storage(self):
        if not hasattr(self, '_files_storage') or not self._files_storage:
            try:
                self._files_storage = MinioStorage(
                    minio_host=self.config.host,
                    minio_access_key=self.config.access_key,
                    minio_secret_key=self.config.secret_key,
                    bucket_root=self.config.bucket_root,
                    bucket_subdir=self.config.bucket_app_subdir,
                    minio_secure=self.config.secure,
                    minio_http_client=None,
                )
            except Exception as e:
                raise exceptions.GetFilesStorageError(
                    _("Unable to get MinioStorage {} {} {}").format(
                        self.config, type(e), e
                    )
                )
        return self._files_storage

    @property
    def bucket_app_subdir(self):
        return self.config.bucket_app_subdir

    def _push_file(self, source_filepath, subdirs, preserve_name):
        """
        Isola a chamada para armazenar o arquivo
        """
        response = self.files_storage.register(
            source_filepath,
            subdirs=subdirs,
            preserve_name=preserve_name,
        )
        logging.info("Response %s %s" % (source_filepath, response))
        return response['uri']

    def push_file(self, source_filepath, subdirs, preserve_name):
        basename = os.path.basename(source_filepath)
        subdirs = os.path.join(self.bucket_app_subdir, subdirs)
        logging.info("Register {} {}".format(source_filepath, subdirs))

        try:
            uri = self._push_file(source_filepath, subdirs, preserve_name)
            return {"uri": uri, "basename": basename}
        except MinioStorageRegisterError as e:
            raise exceptions.PushFileError(
                _("Unable to push file {} {} {} {}").format(
                    source_filepath, subdirs, type(e), e
                )
            )

    def _push_xml_content(self, content, mimetype, object_name):
        """
        Isola a chamada para armazenar o conteúdo do arquivo
        """
        return self.files_storage.fput_content(
            content,
            mimetype=mimetype,
            object_name=object_name,
        )

    def push_xml_content(self, filename, subdirs, content, finger_print):
        mimetype = "text/xml"
        name, ext = os.path.splitext(filename)

        object_name = f"{name}/{finger_print}/{filename}"
        if subdirs:
            object_name = f"{subdirs}/{object_name}"

        try:
            uri = self._push_xml_content(
                content,
                mimetype=mimetype,
                object_name=f"{self.bucket_app_subdir}/{object_name}",
            )
            return {"uri": uri}
        except MinioStorageFPutContentError as e:
            raise exceptions.PutXMLContentError(
                _("Unable to push xml content {} {} {} {}").format(
                    filename, subdirs, type(e), e
                )
            )
