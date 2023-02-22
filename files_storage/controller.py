import logging
import os

from django.utils.translation import gettext_lazy as _

from files_storage.utils import generate_finger_print
from files_storage.models import (
    MinioConfiguration,
    MinioFile,
)
from files_storage.minio import MinioStorage
from files_storage import exceptions


def get_files_storage(files_storage_config):
    try:
        return MinioStorage(
            minio_host=files_storage_config.host,
            minio_access_key=files_storage_config.access_key,
            minio_secret_key=files_storage_config.secret_key,
            bucket_root=files_storage_config.bucket_root,
            bucket_subdir=files_storage_config.bucket_app_subdir,
            minio_secure=files_storage_config.secure,
            minio_http_client=None,
        )
    except Exception as e:
        raise exceptions.GetFilesStorageError(
            _("Unable to get MinioStorage {} {} {}").format(
                files_storage_config, type(e), e)
        )


class FilesStorageManager:

    def __init__(self, files_storage_name):
        self.config = MinioConfiguration.get_or_create(name=files_storage_name)
        self.files_storage = get_files_storage(self.config)

    def push_pid_provider_xml(self, versions, filename, content, creator):
        try:
            finger_print = generate_finger_print(content)
            if versions.latest_version and finger_print == versions.latest_version.finger_print:
                return

            name, extension = os.path.splitext(filename)
            if extension == '.xml':
                mimetype = "text/xml"

            object_name = f"{name}/{finger_print}/{name}{extension}"
            uri = self.files_storage.fput_content(
                content,
                mimetype=mimetype,
                object_name=f"{self.config.bucket_app_subdir}/{object_name}",
            )
            logging.info(uri)
            versions.add_version(
                uri=uri, creator=creator, basename=f"{name}{extension}",
                finger_print=finger_print,
            )
        except Exception as e:
            raise exceptions.PushPidProviderXMLError(
                _("Unable to register pid provider XML {} {} {}").format(
                    filename, type(e), e
                )
            )

    def push_file(self, source_filename, subdirs, preserve_name):
        try:
            basename = os.path.basename(source_filename)
            subdirs = os.path.join(self.config.bucket_app_subdir, subdirs)
            logging.info("Register {} {}".format(source_filename, subdirs))

            response = self.files_storage.register(
                source_filename,
                subdirs=subdirs,
                preserve_name=preserve_name,
            )
            logging.info("Response %s %s" % (source_filename, response))
            return {"uri": response['uri'], "basename": basename}
        except Exception as e:
            raise exceptions.PushFileError(
                _("Unable to push file {} {} {} {}").format(
                    source_filename, subdirs, type(e), e
                )
            )

    def push_xml_content(self, filename, subdirs, content):
        try:
            finger_print = generate_finger_print(content)
            name, extension = os.path.splitext(filename)
            if extension == '.xml':
                mimetype = "text/xml"

            object_name = f"{subdirs}/{name}/{finger_print}/{name}{extension}"
            uri = self.files_storage.fput_content(
                content.decode("utf-8"),
                mimetype=mimetype,
                object_name=f"{self.config.bucket_app_subdir}/{object_name}",
            )
            return {"uri": uri, "basename": filename}
        except Exception as e:
            raise exceptions.PutXMLContentError(
                _("Unable to push file {} {} {} {}").format(
                    filename, subdirs, type(e), e
                )
            )
