import logging
from datetime import datetime

from django.core.files.base import ContentFile
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext as _
from django.db.utils import IntegrityError
from lxml import etree
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre
from wagtail.admin.panels import FieldPanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField

LOGGER = logging.getLogger(__name__)
LOGGER_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class XMLJournalGetError(Exception):
    ...


class XMLJournalCreateError(Exception):
    ...


class XMLIssueGetError(Exception):
    ...


class XMLIssueCreateError(Exception):
    ...


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

    class Meta:
        indexes = [
            models.Index(fields=["finger_print"]),
            models.Index(fields=["pid_v3"]),
        ]

    def __str__(self):
        return str(
            dict(
                pid_v3=self.pid_v3,
                created=self.created.isoformat(),
                xml=self.xml_with_pre.tostring(),
            )
        )

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
    def get_or_create(cls, issn_electronic=None, issn_print=None):
        try:
            return cls.get(
                issn_electronic=issn_electronic,
                issn_print=issn_print,
            )
        except (cls.DoesNotExist, IndexError):
            return cls.create(
                issn_electronic=issn_electronic,
                issn_print=issn_print,
            )

    @classmethod
    def get(cls, issn_electronic=None, issn_print=None):
        if issn_electronic and issn_print:
            return cls.objects.filter(
                issn_electronic=issn_electronic, issn_print=issn_print
            )[0]
        if issn_electronic:
            return cls.objects.filter(issn_electronic=issn_electronic)[0]
        if issn_print:
            return cls.objects.filter(issn_print=issn_print)[0]
        raise XMLJournalGetError(
            "XMLJournal.get requires issn_electronic or issn_print"
        )

    @classmethod
    def create(cls, issn_electronic=None, issn_print=None):
        if not issn_electronic and not issn_print:
            raise XMLJournalCreateError(
                "XMLJournal.create requires issn_electronic or issn_print"
            )

        try:
            obj = cls(issn_electronic=issn_electronic, issn_print=issn_print)
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(issn_electronic, issn_print)


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
    def get(cls, journal, volume, number, suppl, pub_year):
        if journal is None:
            raise XMLIssueGetError(f"XMLIssue.get requires journal")
        if pub_year is None:
            raise XMLIssueGetError(f"XMLIssue.get requires pub_year")
        try:
            # mesmo com tratamento de exceção DoesNotExist, o registro duplica
            return cls.objects.filter(
                journal=journal,
                volume=volume,
                number=number,
                suppl=suppl,
                pub_year=pub_year,
            )[0]
        except IndexError:
            raise cls.DoesNotExist()

    @classmethod
    def create(cls, journal, volume, number, suppl, pub_year):
        if journal is None:
            raise XMLIssueCreateError(f"XMLIssue.create requires journal")
        if pub_year is None:
            raise XMLIssueCreateError(f"XMLIssue.create requires pub_year")
        try:
            issue = cls(
                journal=journal,
                volume=volume,
                number=number,
                suppl=suppl,
                pub_year=pub_year,
            )
            issue.save()
            return issue
        except IntegrityError:
            return cls.get(
                journal=journal,
                volume=volume,
                number=number,
                suppl=suppl,
                pub_year=pub_year,
            )

    @classmethod
    def get_or_create(cls, journal, volume, number, suppl, pub_year):
        try:
            return cls.get(
                journal=journal,
                volume=volume,
                number=number,
                suppl=suppl,
                pub_year=pub_year,
            )
        except cls.DoesNotExist:
            return cls.create(
                journal=journal,
                volume=volume,
                number=number,
                suppl=suppl,
                pub_year=pub_year,
            )


class XMLSPS(CommonControlField):
    is_published = models.BooleanField(_("Is published"), null=True, blank=True)
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

    base_form_class = CoreAdminModelForm

    panels = [
        FieldPanel("is_published"),
        FieldPanel("pid_v3"),
        FieldPanel("pid_v2"),
        FieldPanel("aop_pid"),
        FieldPanel("xml_journal"),
        FieldPanel("xml_issue"),
        FieldPanel("xml_version"),
    ]

    class Meta:
        indexes = [
            models.Index(fields=["pid_v2"]),
            models.Index(fields=["pid_v3"]),
            models.Index(fields=["aop_pid"]),
        ]

    def __str__(self):
        return f"{self.pid_v3} {self.pid_v2} {self.aop_pid}"

    @classmethod
    def list(cls, from_date):
        return XMLSPS.objects.filter(
            Q(created__gte=from_date) | Q(updated__gte=from_date),
        ).iterator()

    @property
    def xml(self):
        return self.xml_version.xml

    @property
    def xml_with_pre(self):
        return self.xml_version.xml_with_pre

    @classmethod
    def get(cls, pid_v3):
        return cls.objects.get(pid_v3=pid_v3)

    @classmethod
    def create_or_update(
        cls,
        pid_v3,
        pid_v2,
        aop_pid,
        xml_version,
        xml_journal,
        xml_issue,
        user,
        is_published,
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
        obj.is_published = is_published
        obj.save()
        return obj
