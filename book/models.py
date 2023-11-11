from django.db import models
from django.utils.translation import gettext as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from book.forms import BookModelForm, ChapterModelForm
from core.choices import LANGUAGE
from core.models import CommonControlField, Language
from institution.models import Institution
from location.models import Location
from researcher.models import Researcher


class Book(CommonControlField, ClusterableModel):
    """
    A class to represent a book model designed in the SciELO context.

    Attributes
    ----------
    location = Country, State and City model
    institution = the publisher that in general is a institution
    isbn = the International Standard Book Number of the book
    eisbn = the electronic International Standard Book Number of the book
    language = the language with a closed list
    synopsis = a short description of the contents
    title = the title of the book
    year = the year with max_length = 4
    doi = the Digital Object Identifier of the book
    researcher = the authors

    CommonControlField:
        created = date of creation the data in this database
        updated = date of the latest update
        creator = the user create the data
        updated_by = the user last update the data.

    Methods
    -------
    TODO
    """

    title = models.TextField(_("Title"), null=True, blank=True)
    synopsis = models.TextField(_("Synopsis"), null=True, blank=True)
    isbn = models.CharField("ISBN", max_length=13, null=True, blank=True)
    eisbn = models.CharField(_("Electronic ISBN"), max_length=13, null=True, blank=True)
    doi = models.CharField("DOI", max_length=256, null=True, blank=True)  # FK DOI
    year = models.IntegerField(_("Year"), null=True, blank=True)
    identifier = models.URLField(max_length=200, null=True, blank=True)
    researchers = models.ManyToManyField(
        Researcher, verbose_name=_("Authors"), blank=True
    )
    language = models.ForeignKey(
        Language,
        verbose_name=_("Language"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    location = models.ForeignKey(
        Location,
        verbose_name=_("Localization"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    institution = models.ForeignKey(
        Institution,
        verbose_name=_("Publisher"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = _("SciELO Book")
        verbose_name_plural = _("SciELO Books")
        indexes = [
            models.Index(
                fields=[
                    "isbn",
                ]
            ),
            models.Index(
                fields=[
                    "title",
                ]
            ),
            models.Index(
                fields=[
                    "synopsis",
                ]
            ),
            models.Index(
                fields=[
                    "doi",
                ]
            ),
            models.Index(
                fields=[
                    "eisbn",
                ]
            ),
            models.Index(
                fields=[
                    "year",
                ]
            ),
            models.Index(
                fields=[
                    "identifier",
                ]
            ),
        ]

    panels_identification = [
        FieldPanel("title"),
        AutocompletePanel("researchers"),
        FieldPanel("synopsis"),
        FieldPanel("isbn"),
        FieldPanel("eisbn"),
        FieldPanel("doi"),
        FieldPanel("identifier"),
        FieldPanel("year"),
        AutocompletePanel("language"),
        AutocompletePanel("location"),
        AutocompletePanel("institution"),
        InlinePanel("rec_raws", label="Rec Raws"),
    ]

    panels_chapter = [
        InlinePanel("chapter", label=_("Chapter"), classname="collapsed"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_identification, heading=_("Identification")),
            ObjectList(panels_chapter, heading=_("Chapters")),
        ]
    )

    def __unicode__(self):
        return "%s" % self.title or ""

    def __str__(self):
        return "%s" % self.title or ""

    @classmethod
    def get(cls, identifier=None, doi=None, isbn=None, eisbn=None):
        if doi:
            return cls.objects.get(doi=doi)
        if isbn:
            return cls.objects.get(isbn=isbn)
        if eisbn:
            return cls.objects.get(eisbn=eisbn)
        if identifier:
            return cls.objects.get(identifier=identifier)
        raise ValueError("Books.get requires doi, isbn, eisbn or identifier parameters")

    @classmethod
    def create_or_update(
        cls,
        user,
        doi,
        isbn,
        eisbn,
        identifier,
        title,
        synopsis,
        year,
        researchers,
        language,
        location,
        institution,
    ):
        try:
            obj = cls.get(doi=doi, isbn=isbn, eisbn=eisbn, identifier=identifier)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls(creator=user)

        obj.doi = doi or obj.doi
        obj.isbn = isbn or obj.isbn
        obj.eisbn = eisbn or obj.eisbn
        obj.title = title or obj.title
        obj.identifier = identifier or obj.identifier
        obj.synopsis = synopsis or obj.synopsis
        obj.year = year or obj.year
        obj.language = language or obj.language
        obj.location = location or obj.location
        obj.institution = institution or obj.institution
        obj.save()
        if researchers:
            obj.researchers.set(researchers)
        return obj

    base_form_class = BookModelForm


class Chapter(Orderable, CommonControlField):
    """
    A class to represent a part of book (chapter) model designed in the SciELO context.

    Attributes
    ----------
    title = the title of the chapter
    language = the language with a closed list
    publication_date = the publication date

    Methods
    -------
    TODO
    """

    book = ParentalKey(Book, on_delete=models.CASCADE, related_name="chapter")

    title = models.CharField(_("Title"), max_length=256, null=True, blank=True)
    publication_date = models.CharField(
        _("Data de publicação"), max_length=10, null=True, blank=True
    )
    language = models.ForeignKey(
        Language,
        verbose_name=_("Language"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    panels = [
        FieldPanel("title"),
        FieldPanel("publication_date"),
        AutocompletePanel("language"),
    ]

    class Meta:
        verbose_name = _("Chapter")
        verbose_name_plural = _("Chapters")
        indexes = [
            models.Index(
                fields=[
                    "title",
                ]
            ),
            models.Index(
                fields=[
                    "language",
                ]
            ),
            models.Index(
                fields=[
                    "publication_date",
                ]
            ),
            models.Index(
                fields=[
                    "book",
                ]
            ),
        ]

    def __unicode__(self):
        return "%s" % self.title or ""

    def __str__(self):
        return "%s" % self.title or ""

    base_form_class = ChapterModelForm


class RecRaw(Orderable, CommonControlField):
    """
    A class to represent a raw record element in XML format, designed within the context of SciELO.

    Attributes
    ----------
    book : Book
        The related Book object to which this raw record belongs (can be blank or null).
    rec : str
        The XML representation of the record element from OAI-PMH.

    Methods
    -------
    TODO
    """

    book = ParentalKey(
        Book, on_delete=models.SET_NULL, blank=True, null=True, related_name="rec_raws"
    )
    rec = models.TextField(blank=True, null=True)

    panels = [FieldPanel("rec")]

    def __str__(self):
        return f"{self.rec} - {self.book}"
