import logging
from datetime import datetime

from django.core.files.base import ContentFile
from django.db import models
from django.db.models import Q
from django.db.utils import IntegrityError
from django.utils.translation import gettext as _
from lxml import etree
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField

LOGGER = logging.getLogger(__name__)
LOGGER_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class XMLVersionXmlWithPreError(Exception):
    ...


class XMLVersionLatestError(Exception):
    ...


class XMLVersionGetError(Exception):
    ...


def xml_directory_path(instance, subdir):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return f"xml_pid_provider/{subdir}/{instance.pid_v3[0]}/{instance.pid_v3[-1]}/{instance.pid_v3}/{instance.finger_print}.zip"


class XMLVersion(CommonControlField):
    """
    Tem função de guardar a versão do XML
    """

    pid_v3 = models.CharField(_("PID v3"), max_length=23, null=True, blank=True)
    file = models.FileField(upload_to=xml_directory_path, null=True, blank=True)
    finger_print = models.CharField(max_length=64, null=True, blank=True)

    panels = [
        FieldPanel("file", read_only=True, permission="superuser"),
    ]

    # autocomplete_search_field = "pid_v3"

    def autocomplete_label(self):
        return self.pid_v3

    class Meta:
        indexes = [
            models.Index(fields=["finger_print"]),
            models.Index(fields=["pid_v3"]),
        ]

    def __str__(self):
        return self.pid_v3

    @classmethod
    def create(
        cls,
        creator,
        xml_with_pre,
    ):
        pid_v3 = xml_with_pre.v3
        sps_pkg_name = xml_with_pre.sps_pkg_name
        logging.info(f"XMLVersion.create({sps_pkg_name})")
        subdir = sps_pkg_name[:9]

        obj = cls()
        obj.pid_v3 = pid_v3
        obj.finger_print = xml_with_pre.finger_print
        obj.creator = creator
        obj.created = datetime.utcnow()
        obj.save()
        obj.save_file(subdir, xml_with_pre.get_zip_content(f"{sps_pkg_name}.xml"))
        obj.save()
        return obj

    def save_file(self, subdir, content):
        self.file.save(subdir, ContentFile(content))

    @property
    def xml_with_pre(self):
        try:
            for item in XMLWithPre.create(path=self.file.path):
                return item
        except Exception as e:
            raise XMLVersionXmlWithPreError(
                _("Unable to get xml with pre (XMLVersion) {}: {} {}").format(
                    self.pid_v3, type(e), e
                )
            )

    @property
    def xml(self):
        try:
            return self.xml_with_pre.tostring()
        except XMLVersionXmlWithPreError as e:
            return str(e)

    @classmethod
    def latest(cls, pid_v3):
        if pid_v3:
            return cls.objects.filter(pid_v3=pid_v3).latest("created")
        raise XMLVersionLatestError(
            "XMLVersion.get requires pid_v3 and xml_with_pre parameters"
        )

    @classmethod
    def get(cls, pid_v3, finger_print):
        """
        Retorna última versão se finger_print corresponde
        """
        if not pid_v3 and not finger_print:
            raise XMLVersionGetError(
                "XMLVersion.get requires pid_v3 and xml_with_pre parameters"
            )

        latest = cls.latest(pid_v3)
        if latest.finger_print == finger_print:
            return latest
        raise cls.DoesNotExist(f"{pid_v3} {finger_print}")

    @classmethod
    def get_or_create(cls, user, xml_with_pre):
        try:
            return cls.get(xml_with_pre.v3, xml_with_pre.finger_print)
        except cls.DoesNotExist:
            return cls.create(
                creator=user,
                xml_with_pre=xml_with_pre,
            )
