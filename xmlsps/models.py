import logging

from django.db import models
from django.db.models import Q

from django.utils.translation import gettext as _
from lxml import etree

from core.models import CommonControlField

LOGGER = logging.getLogger(__name__)
LOGGER_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


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
            return cls.objects.get(
                journal=journal,
                volume=volume,
                number=number,
                suppl=suppl,
                pub_year=pub_year,
            )
        except cls.DoesNotExist:
            issue = cls()
            issue.journal = journal
            issue.volume = volume
            issue.number = number
            issue.suppl = suppl
            issue.pub_year = pub_year
            issue.save()
            return issue


class XMLSPS(CommonControlField):
    xml = models.TextField(_("XML"), null=True, blank=True)
    pid_v3 = models.CharField(_("PID V3"), max_length=23, null=True, blank=True)
    pid_v2 = models.CharField(_("PID V2"), max_length=23, null=True, blank=True)
    aop_pid = models.CharField(_("AOP PID"), max_length=23, null=True, blank=True)
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
    def xmltree(self):
        return etree.fromstring(self.xml)

    @classmethod
    def get(cls, pid_v3):
        return cls.objects.get(pid_v3=pid_v3)

    @classmethod
    def create_or_update(
        cls, pid_v3, pid_v2, aop_pid, xml, xml_journal, xml_issue, user
    ):
        try:
            obj = cls.get(pid_v3=pid_v3)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.pid_v3 = pid_v3
            obj.creator = user
        obj.xml = xml
        obj.pid_v2 = pid_v2
        obj.aop_pid = aop_pid
        obj.xml_issue = xml_issue
        obj.xml_journal = xml_journal
        obj.save()
        return obj
