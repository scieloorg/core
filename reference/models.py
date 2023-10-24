from django.db import models
from core.models import CommonControlField
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel
from django.utils.translation import gettext_lazy as _
# Create your models here.


class JournalTitle(CommonControlField):
    title = models.TextField(null=True, blank=True) 

    def __str__(self):
        return f"{self.title}"


class PubId(models.Model):
    pub_id_type = models.CharField(
        _("Pub Id type"), max_length=10, blank=True, null=True
    )
    pub_id_value = models.CharField(
        _("Pub Id value"), max_length=10, blank=True, null=True
    )

    def __unicode__(self):
        return "%s | %s" % (self.pub_id_type, self.pub_id_value)

    def __str__(self):
        return "%s | %s" % (self.pub_id_type, self.pub_id_value)


class AuthorInReference(CommonControlField):
    given_names = models.CharField(
        _("Given names"), max_length=128, blank=True, null=True
    )
    last_name = models.CharField(_("Last name"), max_length=128, blank=True, null=True)

    def __unicode__(self):
        return "%s | %s" % (self.given_names, self.last_name)

    def __str__(self):
        return "%s | %s" % (self.given_names, self.last_name)

    @classmethod
    def get_or_create(cls, author, given_names, last_name, user):
        try:
            if author:
                return cls.objects.get(given_names=author.given_names, last_name=author.last_name)
            return cls.objects.get(given_names=given_names, last_name=last_name)
        except cls.DoesNotExist:
            author_in_reference = cls(creator = user)
            author_in_reference.given_names = given_names
            authauthor_in_referenceor.last_name = last_name
            author_in_reference.save()
            return author_in_reference


class Reference(CommonControlField):
    source = models.CharField(
        _("Source"), max_length=10, blank=True, null=True
    )
    authors = models.ManyToManyField(
        AuthorInReference, verbose_name=_("Authors"), blank=True
    )
    volume = models.CharField(
        _("Volume"), max_length=10, blank=True, null=True
    )
    issue = models.CharField(
        _("Issue"), max_length=10, blank=True, null=True
    )
    fpage = models.CharField(
        _("Fpage"), max_length=10, blank=True, null=True
    )
    lpage = models.CharField(
        _("Lpage"), max_length=10, blank=True, null=True
    )
    elocation_id = models.CharField(
        _("Elocation Id"), max_length=10, blank=True, null=True
    )
    doi = models.TextField(_("DOI"), blank=True, null=True)
    year = models.CharField(
        _("Year"), max_length=4, blank=True, null=True
    )
    article_title = RichTextField(_("Article title"), null=True, blank=True)
    citation_ids = models.ManyToManyField(
        PubId, verbose_name=_("Pub Id"), blank=True
    )
    
    panels = [
        FieldPanel("source"),
        AutocompletePanel("authors"),
        FieldPanel("volume"),
        FieldPanel("issue"),
        FieldPanel("fpage"),
        FieldPanel("lpage"),
        FieldPanel("elocation_id"),
        FieldPanel("doi"),
        FieldPanel("year"),
        FieldPanel("article_title"),
        AutocompletePanel("citation_ids"),        
    ]

    def __unicode__(self):
        return "%s | %s | %s | %s | %s" % (self.source, self.year, self.volume, self.issue, self.fpage)

    def __str__(self):
        return "%s | %s | %s | %s | %s" % (self.source, self.year, self.volume, self.issue, self.fpage)

    @classmethod
    def get(
        cls,
        source,
        authors,
        article_title,
        year,
        doi,
        citation_ids,
        volume,
        issue,
        fpage,
        elocation_id
    ):
        q = None

        for item in citation_ids:
            if q is None:
                q = Q(citation_ids__pub_id_value=item.pub_id_value)
            else:
                q = q & Q(citation_ids__pub_id_value=item.pub_id_value)

        if doi or citation_ids:
            reference = cls.objects.get(Q(doi__icontains=doi) | q)
            return reference

        q = None

        for item in authors:
            if q is None:
                q = Q(authors__last_name=item.last_name, authors__given_names=item.given_names)
            else:
                q = q & Q(author__last_name=item.last_name, author__given_names=item.given_names)

        if source and q and article_title and year:
            reference = cls.objects.get(q, source=source, article_title=article_title, year=year)
            return reference

        if source and q and article_title and year and fpage:
            reference = cls.objects.get(q, source=source, article_title=article_title, year=year, fpage=fpage)
            return reference

        if source and q and article_title and year and volume and issue and elocation_id:
            reference = cls.objects.get(q, source=source, article_title=article_title, volume=volume, issue=issue, elocation_id=elocation_id)
            return reference

        raise TypeError("Reference.get requires more paramenters")

    def create_or_update(
        cls,
        source,
        authors,
        volume,
        issue,
        fpage,
        lpage,
        elocation_id,
        doi,
        article_title,
        citation_ids,
        user
    ):
        try:
            obj = cls.get(
                        source=source,
                        authors=authors,
                        article_title=article_title,
                        year=year,
                        doi=doi,
                        citation_ids=citation_ids,
                        volume=volume,
                        issue=issue,
                        fpage=fpage,
                        lpage=lpage,
                        elication_id=elication_id
                        )
            obj.updated_by = user
        except (cls.DoesNotExist, ValueError):
            obj = cls(creator=user)
            obj.source = source or obj.source
            obj.authors = authors or obj.authors
            obj.article_title = article_title or obj.article_title
            obj.year = year or obj.year
            obj.doi = doi or obj.doi
            obj.citation_ids = citation_ids or obj.citation_ids
            obj.volume = volume or obj.volume
            obj.issue = issue or obj.issue
            obj.fpage = fpage or obj.fpage
            obj.lpage = lpage or obj.lpage
            obj.elication_id = elication_id or obj.elication_id
            obj.save()
            return obj

