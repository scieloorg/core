import logging
from datetime import datetime

from django.core.files.base import ContentFile
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext as _
from lxml import etree

from core.models import CommonControlField
from xmlsps.xml_sps_lib import XMLWithPre

LOGGER = logging.getLogger(__name__)
LOGGER_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class XMLVersionXmlWithPreError(Exception):
    ...


def xml_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return f"xml_pid_provider/{instance.finger_print[-1]}/{instance.finger_print[-2]}/{instance.finger_print}/{filename}"


class XMLVersion(CommonControlField):
    """
    Tem função de guardar a versão do XML
    """

    pid_v3 = models.CharField(_("PID v3"), max_length=23, null=True, blank=True)
    file = models.FileField(upload_to=xml_directory_path, null=True, blank=True)
    finger_print = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["finger_print"]),
            models.Index(fields=["pid_v3"]),
        ]

    def __str__(self):
        return self.finger_print

    @classmethod
    def create(
        cls,
        creator,
        pid_v3,
        pkg_name=None,
        finger_print=None,
        zip_xml_content=None,
    ):
        logging.info(f"XMLVersion.create({pkg_name})")
        obj = cls()
        obj.finger_print = finger_print
        obj.pkg_name = pkg_name
        obj.save_file(pkg_name + ".zip", zip_xml_content)
        obj.creator = creator
        obj.created = datetime.utcnow()
        obj.save()

        # salvar pid_v3 e salvar self para evitar exceção
        obj.pid_v3 = pid_v3
        obj.save()
        return obj

    def save_file(self, name, content):
        self.file.save(name, ContentFile(content))

    @property
    def xml_with_pre(self):
        try:
            for item in XMLWithPre.create(path=self.file.path):
                return item
        except Exception as e:
            raise XMLVersionXmlWithPreError(
                _("Unable to get xml with pre (XMLVersion) {}: {} {}").format(
                    self.pkg_name, type(e), e
                )
            )


class XMLJournal(models.Model):
    """
    Tem função de guardar os dados de Journal encontrados no XML
    Tem objetivo de identificar o Documento (Artigo)
    """

    issn_electronic = models.CharField(
        _("issn_epub"), max_length=9, null=True, blank=True
    )
    issn_print = models.CharField(_("issn_ppub"), max_length=9, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["issn_electronic"]),
            models.Index(fields=["issn_print"]),
        ]

    def __str__(self):
        return f"{self.issn_electronic} {self.issn_print}"

    @classmethod
    def get_or_create(cls, issn_electronic, issn_print):
        try:
            return cls.objects.get(
                issn_electronic=issn_electronic,
                issn_print=issn_print,
            )
        except cls.DoesNotExist:
            journal = cls()
            journal.issn_electronic = issn_electronic
            journal.issn_print = issn_print
            journal.save()
            return journal
        except cls.MultipleObjectsReturned:
            # talvez tenha duplicado devido ao registro simultaneo
            # nao é um problema duplicar
            return cls.objects.filter(
                issn_electronic=issn_electronic,
                issn_print=issn_print,
            ).first()


class XMLIssue(models.Model):
    """
    Tem função de guardar os dados de Issue encontrados no XML
    Tem objetivo de identificar o Documento (Artigo)
    """

    journal = models.ForeignKey(
        XMLJournal, on_delete=models.SET_NULL, null=True, blank=True
    )
    pub_year = models.CharField(_("pub_year"), max_length=4, null=True, blank=True)
    volume = models.CharField(_("volume"), max_length=10, null=True, blank=True)
    number = models.CharField(_("number"), max_length=10, null=True, blank=True)
    suppl = models.CharField(_("suppl"), max_length=10, null=True, blank=True)

    class Meta:
        unique_together = [
            ["journal", "pub_year", "volume", "number", "suppl"],
        ]
        indexes = [
            models.Index(fields=["journal"]),
            models.Index(fields=["volume"]),
            models.Index(fields=["number"]),
            models.Index(fields=["suppl"]),
            models.Index(fields=["pub_year"]),
        ]

    def __str__(self):
        return (
            f'{self.journal} {self.volume or ""} {self.number or ""} {self.suppl or ""}'
        )

    @classmethod
    def get_or_create(cls, journal, volume, number, suppl, pub_year):
        try:
            obj = cls.objects.get(
                journal=journal,
                volume=volume,
                number=number,
                suppl=suppl,
                pub_year=pub_year,
            )
            return obj
        except cls.DoesNotExist:
            issue = cls()
            issue.journal = journal
            issue.volume = volume
            issue.number = number
            issue.suppl = suppl
            issue.pub_year = pub_year
            issue.save()
            return issue
        except cls.MultipleObjectsReturned:
            # talvez tenha duplicado devido ao registro simultaneo
            # nao é um problema duplicar
            return cls.objects.filter(
                journal=journal,
                volume=volume,
                number=number,
                suppl=suppl,
                pub_year=pub_year,
            ).first()


class XMLSPS(CommonControlField):
    pid_v3 = models.CharField(_("PID V3"), max_length=23, null=True, blank=True)
    pid_v2 = models.CharField(_("PID V2"), max_length=23, null=True, blank=True)
    aop_pid = models.CharField(_("AOP PID"), max_length=23, null=True, blank=True)
    xml_version = models.ForeignKey(
        XMLVersion, null=True, blank=True, on_delete=models.SET_NULL
    )
    xml_journal = models.ForeignKey(
        XMLJournal, null=True, blank=True, on_delete=models.SET_NULL
    )
    xml_issue = models.ForeignKey(
        XMLIssue, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        indexes = [
            models.Index(fields=["pid_v2"]),
            models.Index(fields=["pid_v3"]),
            models.Index(fields=["aop_pid"]),
            models.Index(fields=["xml_journal"]),
            models.Index(fields=["xml_issue"]),
        ]

    @classmethod
    def list(cls, from_date):
        return XMLSPS.objects.filter(
            Q(created__gte=from_date) | Q(updated__gte=from_date),
        ).iterator()

    @property
    def xml(self):
        return self.xml_version.xml_with_pre.tostring()

    @property
    def xml_with_pre(self):
        return self.xml_version.xml_with_pre

    @property
    def xmltree(self):
        return self.xml_version.xml_with_pre.xmltree

    @classmethod
    def get(cls, pid_v3):
        return cls.objects.get(pid_v3=pid_v3)

    @classmethod
    def create_or_update(
        cls, pid_v3, pid_v2, aop_pid, xml_version, xml_journal, xml_issue, user
    ):
        try:
            obj = cls.get(pid_v3=pid_v3)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.pid_v3 = pid_v3
            obj.creator = user
        obj.pid_v2 = pid_v2 or obj.pid_v2
        obj.aop_pid = aop_pid or obj.aop_pid
        obj.xml_version = xml_version or obj.xml_version
        obj.xml_issue = xml_issue or obj.xml_issue
        obj.xml_journal = xml_journal or obj.xml_journal
        obj.save()
        return obj
