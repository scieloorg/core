from django.db import models


class Dataset(models.Model):
    name = models.TextField(null=True, blank=True)
    dataset_id = models.PositiveIntegerField(null=True, blank=True)
    file_id = models.PositiveIntegerField(null=True, blank=True)
    authors = models.ManyToManyField('Author', blank=True)
    contacts = models.ManyToManyField('Contact', blank=True)
    datasources = models.ManyToManyField('Datasource', blank=True)
    keywords = models.ManyToManyField('Keyword', blank=True)
    producers = models.ManyToManyField('Producer', blank=True)
    publications = models.ManyToManyField('Publication', blank=True)
    subjects = models.ManyToManyField('Subject', blank=True)

    def __str__(self):
        return f"{self.name}"


class Checksum(models.Model):
    type_field = models.CharField(max_length=20, null=True, blank=True)
    value_field = models.CharField(max_length=40, null=True, blank=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.type_field}"


class Author(models.Model):
    surname = models.CharField(max_length=300, null=True, blank=True)
    given_name = models.CharField(max_length=300)

    def __str__(self):
        return f"{self.given_name}, {self.surname}"


class Affiliation(models.Model):
    name = models.TextField(Unique=True)

    def __str__(self):
        return f"{self.name}"


class Contact(models.Model):
    name = models.CharField(max_length=300, Unique=True)
    affiliation = models.ForeignKey(
        Affiliation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.name}"


class Datasource(models.Model):
    title = models.TextField(Unique=True)

    def __str__(self):
        return f"{self.title}"


class Keyword(models.Model):
    name = models.CharField(max_length=255, Unique=True)

    def __str__(self):
        return f"{self.name}"


class Producer(models.Model):
    name = models.CharField(max_length=300, Unique=True)

    def __str__(self):
        return f"{self.name}"


class Publication(models.Model):
    citation = models.TextField(null=True, blank=True)
    url = models.URLField(max_length=200, null=True, blank=True)

    def __str__(self):
        if self.citation:
            return f"{self.citation}"
        return f"{self.url}"


class Subject(models.Model):
    title = models.TextField(Unique=True)

    def __str__(self):
        return f"{self.title}"
