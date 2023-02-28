from django.db import models
from core.models import CommonControlField


class Dataset(CommonControlField):
    name = models.TextField(null=True, blank=True)
    name_of_dataverse = models.TextField(null=True, blank=True)
    citation = models.TextField(null=True, blank=True)
    citationHtml = models.TextField(null=True, blank=True)
    dataset_citation = models.TextField(null=True, blank=True)
    dataset_id = models.PositiveIntegerField(null=True, blank=True)
    dataset_id = models.PositiveIntegerField(null=True, blank=True)
    dataset_name = models.TextField(null=True, blank=True)
    dataset_persistent_id = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    #
    file_content_type = models.CharField(max_length=100, null=True, blank=True)
    file_id = models.PositiveIntegerField(null=True, blank=True)
    file_persistent_id = models.TextField(null=True, blank=True)
    file_type = models.CharField(max_length=25, null=True, blank=True)
    file_count = models.PositiveIntegerField(null=True, blank=True)
    #
    global_id = models.TextField(null=True, blank=True)
    identifier = models.CharField(max_length=15, null=True, blank=True)
    identifier_of_dataverse = models.CharField(max_length=15, null=True, blank=True)
    #
    major_version = models.PositiveIntegerField(null=True, blank=True)
    minor_version = models.PositiveIntegerField(null=True, blank=True)
    md5 = models.CharField(max_length=32, null=True, blank=True)
    #
    published_at = models.DateTimeField(null=True, blank=True)
    publisher = models.ForeignKey(
        'Publisher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    #
    size_in_bytes = models.PositiveIntegerField(null=True, blank=True)
    storage_identifier = models.TextField(null=True, blank=True)
    unf = models.CharField(max_length=30, null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    version_id = models.PositiveIntegerField(null=True, blank=True)
    version_state = models.CharField(max_length=8, null=True, blank=True)
    #
    authors = models.ManyToManyField('Author', blank=True)
    contacts = models.ManyToManyField('Contact', blank=True)
    datasources = models.ManyToManyField('Datasource', blank=True)
    keywords = models.ManyToManyField('Keyword', blank=True)
    producers = models.ManyToManyField('Producer', blank=True)
    publications = models.ManyToManyField('Publication', blank=True)
    subjects = models.ManyToManyField('Subject', blank=True)

    def __str__(self):
        return f'{self.name}'


class Checksum(models.Model):
    type_field = models.CharField(max_length=20, null=True, blank=True)
    value_field = models.CharField(max_length=40, null=True, blank=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f'{self.type_field}'


class Publisher(models.Model):
    name = models.TextField(unique=True)

    def __str__(self):
        return f'{self.name}'


class Author(models.Model):
    surname = models.CharField(max_length=300, null=True, blank=True)
    given_name = models.CharField(max_length=300)

    def __str__(self):
        return f'{self.given_name}, {self.surname}'


class Affiliation(models.Model):
    name = models.TextField(unique=True)

    def __str__(self):
        return f'{self.name}'


class Contact(models.Model):
    name = models.CharField(max_length=300, unique=True)
    affiliation = models.ForeignKey(
        Affiliation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return f'{self.name}'


class Datasource(models.Model):
    title = models.TextField(unique=True)

    def __str__(self):
        return f'{self.title}'


class Keyword(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f'{self.name}'


class Producer(models.Model):
    name = models.CharField(max_length=300, unique=True)

    def __str__(self):
        return f'{self.name}'


class Publication(models.Model):
    citation = models.TextField(null=True, blank=True)
    url = models.URLField(max_length=200, null=True, blank=True)

    def __str__(self):
        if self.citation:
            return f'{self.citation}'
        return f'{self.url}'


class Subject(models.Model):
    title = models.TextField(unique=True)

    def __str__(self):
        return f'{self.title}'
