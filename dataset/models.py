from django.db import models
from django.utils.translation import gettext_lazy as _

from core.forms import CoreAdminModelForm
from core.models import CommonControlField
from thematic_areas.models import ThematicArea
from vocabulary.models import Keyword
from .exceptions import (
    DataverseGetError,
    DataverseCreateOrUpdateError,
    DatasetGetError,
    DatasetCreateOrUpdateError,
    FileGetError,
    FileCreateOrUpdateError,
)


TYPE_CHOICES = [
    ("dataverse", "dataverse"),
    ("dataset", "dataset"),
    ("file", "file"),
]


class CommonDataField(models.Model):
    name = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=9, choices=TYPE_CHOICES, blank=True, null=True)
    url = models.URLField(_("URL"), blank=True, null=True)
    published_at = models.CharField(max_length=25, blank=True, null=True)

    def __unicode__(self):
        return f"{self.name}"

    def __str__(self):
        return f"{self.name}"

    class Meta:
        abstract = True

    base_form_class = CoreAdminModelForm


class Dataverse(CommonControlField, CommonDataField):
    identifier = models.CharField(max_length=30, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    @classmethod
    def get(
        cls,
        name,
        identifier,
    ):
        if identifier:
            return cls.objects.get(identifier=identifier)
        if name:
            return cls.objects.get(name=name)
        raise DataverseGetError()

    @classmethod
    def create_or_update(
        cls,
        user=None,
        name=None,
        identifier=None,
        type=None,
        url=None,
        published_at=None,
        description=None,
    ):
        try:
            obj = cls.get(identifier=identifier, name=name)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.name = name
            obj.identifier = identifier
            obj.creator = user
        except (cls.MultipleObjectsReturned, DataverseCreateOrUpdateError) as e:
            raise DataverseCreateOrUpdateError(e) 

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
    publisher = models.ForeignKey(
        "Publisher", on_delete=models.SET_NULL, blank=True, null=True
    )
    citation_html = models.TextField(blank=True, null=True)
    citation = models.TextField(blank=True, null=True)
    identifier_of_dataverse = models.ForeignKey(
        Dataverse, on_delete=models.SET_NULL, null=True, blank=True
    )
    keywords = models.ManyToManyField(Keyword, blank=True)
    thematic_area = models.ManyToManyField(ThematicArea, blank=True)
    authors = models.ManyToManyField("Author", blank=True)
    contacts = models.ManyToManyField("Affiliation", blank=True)
    publications = models.ManyToManyField(
        "Publication",
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "global_id",
                ]
            ),
        ]

    @classmethod
    def get(cls, global_id):
        if global_id:
                return cls.objects.get(global_id=global_id)
        raise DatasetGetError()

    @classmethod
    def create_or_update(
        cls,
        user,
        global_id=None,
        name=None,
        type=None,
        url=None,
        published_at=None,
        description=None,
        publisher=None,
        citation_html=None,
        citation=None,
        identifier_of_dataverse=None,
        authors=None,
        keywords=None,
        thematic_area=None,
        contacts=None,
        publications=None,
    ):
        try:
            obj = cls.get(global_id=global_id)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.global_id = global_id
            obj.creator = user
        except (DatasetCreateOrUpdateError, cls.MultipleObjectsReturned) as e:
            raise DatasetCreateOrUpdateError(e)

        obj.name = name or obj.name
        obj.description = description or obj.description
        obj.publisher = publisher or obj.publisher
        obj.citation_html = citation_html or obj.citation_html
        obj.citation = citation or obj.citation
        obj.type = type or obj.type
        obj.url = url or obj.url
        obj.published_at = published_at or obj.published_at
        obj.identifier_of_dataverse = identifier_of_dataverse or obj.identifier_of_dataverse
        obj.publisher = publisher or obj.publisher
        obj.save()
        if authors:
            obj.authors.set(authors)
        if keywords:
            obj.keywords.set(keywords)
        if thematic_area:
            obj.thematic_area.set(thematic_area)
        if contacts:
            obj.contacts.set(contacts)
        if publications:
            obj.publications.set(publications)

    base_form_class = CoreAdminModelForm


class File(CommonControlField, CommonDataField):
    file_type = models.CharField(max_length=100, blank=True, null=True)
    file_content_type = models.CharField(max_length=100, blank=True, null=True)
    file_persistent_id = models.TextField(blank=True, null=True)
    dataset_persistent_id = models.ForeignKey(
        Dataset, on_delete=models.SET_NULL, blank=True, null=True
    )

    @classmethod
    def get(
        cls,
        file_persistent_id,
    ):
        if file_persistent_id:
            return cls.objects.get(file_persistent_id=file_persistent_id)
        raise FileGetError()

    @classmethod
    def create_or_update(
        cls,
        user,
        file_persistent_id=None,
        name=None,
        type=None,
        url=None,
        published_at=None,
        file_type=None,
        file_content_type=None,
        dataset_persistent_id=None,
    ):
        try:
            obj = cls.objects.get(file_persistent_id=file_persistent_id)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.file_persistent_id = file_persistent_id
            obj.creator = user
        except (FileCreateOrUpdateError, cls.MultipleObjectsReturned) as e:
            raise FileCreateOrUpdateError(e)

        obj.name = name or obj.name
        obj.type = type or obj.type
        obj.url = url or obj.url
        obj.published_at = published_at or obj.published_at
        obj.file_type = file_type or obj.file_type
        obj.file_content_type = file_content_type or obj.file_content_type
        obj.dataset_persistent_id = dataset_persistent_id or obj.dataset_persistent_id
        obj.save()

    base_form_class = CoreAdminModelForm


class Affiliation(CommonControlField):
    institution = models.ForeignKey(
        "InstitutionDataSet", on_delete=models.SET_NULL, blank=True, null=True
    )
    author = models.ForeignKey(
        "Author",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    def __unicode__(self):
        return f"{self.institution} - {self.author}"

    def __str__(self):
        return f"{self.institution} - {self.author}"


class Publication(CommonControlField):
    citation = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)

    def __unicode__(self):
        return f"{self.citation} - {self.url}"

    def __str__(self):
        return f"{self.citation} - {self.url}"


class Author(CommonControlField):
    name = models.CharField(max_length=100, blank=True, null=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name


class Publisher(CommonControlField):
    name = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name


class InstitutionDataSet(CommonControlField):
    name = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name
