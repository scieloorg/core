from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import CommonControlField
from institution.models import Institution
from issue.models import TocSection
from researcher.models import Researcher
from vocabulary.models import Keyword

# Create your models here.


TYPE_CHOICES = [
    ("dataverse", "dataverse"),
    ("dataset", "dataset"),
    ("file", "file"),
]


class CommonDataField(models.Model):
    name = models.TextField(blank=True, null=True)  # relationship  with journal?
    tpye = models.CharField(max_length=9, choices=TYPE_CHOICES, blank=True, null=True)
    url = models.URLField(_("URL"), blank=True, null=True)
    published_at = models.CharField(max_length=25, blank=True, null=True)


class Dataverse(CommonControlField, CommonDataField):
    identifier = models.CharField(max_length=30, blank=True, null=True)  # source
    description = models.TextField(blank=True, null=True)


class Dataset(CommonControlField, CommonDataField):
    global_id = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    publisher = models.ForeignKey(Institution, blank=True, null=True)
    citationHtml = models.TextField(blank=True, null=True)
    citation = models.TextField(blank=True, null=True)
    dataverse = models.ForeignKey(
        Dataverse, on_delete=models.SET_NULL, null=True, blank=True
    )
    keywords = models.ManyToManyField(Keyword, blank=True, null=True)
    toc_sections = models.ManyToManyField(TocSection, blank=True, null=True)
    authores = models.ManyToManyField(Researcher, blank=True, null=True)
    contacts = models.ManyToManyField("Affliation", null=True, blank=True)
    publications = models.ForeignKey("Publications", blank=True, null=True)


class File(CommonControlField, CommonDataField):
    file_type = models.CharField(max_length=30, blank=True, null=True)
    file_content_type = models.CharField(max_length=100, blank=True, null=True)
    file_persistent_id = models.CharField()
    dataset = models.ForeignKey(Dataset, blank=True, null=True)


class Affliation(CommonControlField):
    name = models.TextField(blank=True, null=True)
    author = models.ForeignKey(Researcher, blank=True, null=True)


class Publications(CommonControlField):
    url = models.URLField(blank=True, null=True)
