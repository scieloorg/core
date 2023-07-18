from django.db import models
from django.utils.translation import gettext_lazy as _
from core.forms import CoreAdminModelForm

from core.models import CommonControlField
from institution.models import Institution
from issue.models import TocSection
from researcher.models import Researcher
from vocabulary.models import Keyword


TYPE_CHOICES = [
    ("dataverse", "dataverse"),
    ("dataset", "dataset"),
    ("file", "file"),
]


class CommonDataField(models.Model):
    name = models.TextField(blank=True, null=True)  # relationship  with journal?
    type = models.CharField(max_length=9, choices=TYPE_CHOICES, blank=True, null=True)
    url = models.URLField(_("URL"), blank=True, null=True)
    published_at = models.CharField(max_length=25, blank=True, null=True)

    class Meta:
        abstract = True

    base_form_class = CoreAdminModelForm


class Dataverse(CommonControlField, CommonDataField):
    identifier = models.CharField(max_length=30, blank=True, null=True)  # source
    description = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return f"{self.name}"

    def __str__(self):
        return f"{self.name} - {self.type}"

    @classmethod
    def create_or_update(
        cls,
        name,
        identifier,
        user=None,
        type=None,
        url=None,
        published_at=None,
        description=None,
    ):
        try:
            obj = cls.objects.get(identifier=identifier)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.name = name
            obj.identifier = identifier
            obj.creator = user

        obj.name = name or obj.name
        obj.identifier = identifier or obj.identifier
        obj.type = type or obj.type
        obj.url = url or obj.url
        obj.published_at = published_at or obj.published_at
        obj.description = description or obj.description
        obj.save()
        return obj

    base_form_class = CoreAdminModelForm


class Dataset(CommonControlField, CommonDataField):
    global_id = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(blank=True, null=True)  # Abstract
    publisher = models.ForeignKey(Institution, on_delete=models.SET_NULL, blank=True, null=True)
    citation_html = models.TextField(blank=True, null=True)
    citation = models.TextField(blank=True, null=True)
    dataverse = models.ForeignKey(
        Dataverse, on_delete=models.SET_NULL, null=True, blank=True
    )
    keywords = models.ManyToManyField(Keyword, blank=True)
    toc_sections = models.ManyToManyField(TocSection, blank=True)
    authors = models.ManyToManyField(Researcher, blank=True)
    contacts = models.ManyToManyField("Affliation", blank=True)
    publications = models.ForeignKey("Publications", on_delete=models.SET_NULL, blank=True, null=True)

    def __unicode__(self):
        return f"{self.name}"

    def __str__(self):
        return f"{self.name} - {self.type}"

    @classmethod
    def create_or_update(
        cls,
        global_id,
        name=None,
        type=None,
        url=None,
        published_at=None,
        description=None,
        publisher=None,
        citation_html=None,
        citation=None,
        dataverse=None,
        authors=None,
        keywords=None,
        toc_sections=None,
        contacts=None,
        publications=None,
    ):
        try:
            obj = cls.objects.get(global_id=global_id)
        except cls.DoesNotExist:
            obj = cls()
            obj.global_id = global_id

        obj.name = name or obj.name
        obj.description = description or obj.description
        obj.publisher = publisher or obj.publisher
        obj.citation_html = citation_html or obj.citation_html
        obj.citation = citation or obj.citation
        obj.type = type or obj.type
        obj.url = url or obj.url
        obj.published_at = published_at or obj.published_at
        ## TODO
        ## Lidar com os campos de ManyToMany e FK
        obj.save()

    base_form_class = CoreAdminModelForm


class File(CommonControlField, CommonDataField):
    file_type = models.CharField(max_length=30, blank=True, null=True)
    file_content_type = models.CharField(max_length=100, blank=True, null=True)
    file_persistent_id = models.TextField(blank=True, null=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.SET_NULL, blank=True, null=True)

    def __unicode__(self):
        return f"{self.name}"

    def __str__(self):
        return f"{self.name} - {self.type}"

    @classmethod
    def create_or_update(
        cls,
        name,
        type=None,
        url=None,
        published_at=None,
        file_type=None,
        file_persistent_type=None,
        file_persistent_id=None,
        dataset=None,
    ):
        try:
            obj = cls.objects.get(file_persistent_id=file_persistent_id)
        except cls.DoesNotExist:
            obj = cls()
            obj.file_persistent_id = file_persistent_id

        obj.name = name or obj.name
        obj.type = type or obj.type
        obj.url = url or obj.url
        obj.published_at = published_at or obj.published_at
        obj.file_type = file_type or obj.file_type
        obj.file_persistent_type = file_persistent_id or obj.file_persistent_id
        ## TODO
        ## Lidar com os campos de ManyToMany e FK
        obj.save()

    base_form_class = CoreAdminModelForm


class Affliation(CommonControlField):
    name = models.TextField(blank=True, null=True)
    author = models.ForeignKey(Researcher, on_delete=models.SET_NULL, blank=True, null=True)


class Publications(CommonControlField):
    citation = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
