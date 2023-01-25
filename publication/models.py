from django.db import models
from django.utils.translation import gettext_lazy as _

from wagtail.admin.edit_handlers import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.models import CommonControlField
from core.forms import CoreAdminModelForm

from .choices import PUBLICATION_TYPE

from issue.models import Issue
from institution.models import Institution


class Author(CommonControlField):
    """
        Class that represents an author
    """

    surname = models.CharField(_('Surname'), max_length=50, null=True, blank=True)
    given_name = models.CharField(_('Given name'), max_length=100, null=True, blank=True)
    affiliation = models.ForeignKey(Institution, verbose_name=_('Affiliation'), null=True,
                                    blank=True, on_delete=models.SET_NULL)

    autocomplete_search_field = 'surname'

    def autocomplete_label(self):
        return self.surname

    class Meta:
        verbose_name = _('Author')
        verbose_name_plural = _('Authors')
        indexes = [
            models.Index(fields=['surname', ]),
            models.Index(fields=['given_name', ]),
        ]

    @property
    def data(self):
        d = {
            'author__surname': self.surname,
            'author__given_name': self.given_name,
        }

        return d

    @classmethod
    def create(cls, surname, given_name, affiliation):
        try:
            author = cls.objects.filter(
                surname=surname,
                given_name=given_name,
                affiliation=affiliation
            )[0]
        except IndexError:
            author = cls()
            author.surname = surname
            author.given_name = given_name
            author.affiliation = affiliation

    def __unicode__(self):
        return u'%s, %s' % (self.surname, self.given_name) or ''

    def __str__(self):
        return u'%s, %s' % (self.surname, self.given_name) or ''

    base_form_class = CoreAdminModelForm


class Publication(CommonControlField):
    """
    Class that represents a publication
    """

    issue = models.ForeignKey(Issue, verbose_name=_('Issue'), null=True,
                                blank=True, on_delete=models.SET_NULL)
    pid = models.CharField(_('Publication ID'), max_length=30, null=True, blank=True)
    pub_type = models.CharField(_('Publication type'), choices=PUBLICATION_TYPE,
                                max_length=30, null=True, blank=True)
    title = models.CharField(_('Publication ID'), max_length=255, null=True, blank=True)
    first_page = models.IntegerField(_('First page'), null=True, blank=True)
    last_page = models.IntegerField(_('Last page'), null=True, blank=True)
    authors = models.ManyToManyField(Author, verbose_name=_("Authors"), blank=True)

    panels = [
        FieldPanel('issue'),
        FieldPanel('pid'),
        FieldPanel('pub_type'),
        FieldPanel('title'),
        FieldPanel('first_page'),
        FieldPanel('last_page'),
        AutocompletePanel('authors'),
    ]

    class Meta:
        verbose_name = _('Publication')
        verbose_name_plural = _('Publications')
        indexes = [
            models.Index(fields=['pid', ]),
            models.Index(fields=['pub_type', ]),
            models.Index(fields=['title', ]),
            models.Index(fields=['first_page', ]),
            models.Index(fields=['last_page', ]),
        ]

    @property
    def data(self):
        d = {}

        if self.issue:
            d.update(self.issue.data)

        d.update({
            'publication__pid': self.pid,
            'publication__pub_type': self.pub_type,
            'publication__title': self.title,
            'publication__first_page': self.first_page,
            'publication__last_page': self.last_page,
            'publication__authors': [a.data for a in self.authors.iterator()],
        })

        return d

    @classmethod
    def get_or_create(cls, issue, pid, pub_type, title, first_page, last_page, authors):
        try:
            publication = cls.objects.filter(
                issue=issue,
                pid=pid,
                pub_type=pub_type,
                title=title,
                first_page=first_page,
                last_page=last_page,
                authors=authors,
            )[0]
        except IndexError:
            publication = cls()
            publication.issue = issue
            publication.pid = pid
            publication.pub_type = pub_type
            publication.title = title
            publication.first_page = first_page
            publication.last_page = last_page
            publication.save()
            for author in authors:
                publication.authors.add(author)
            publication.save()

        return publication

    def __unicode__(self):
        return u'%s - %s' % (self.pid, self.title) or ''

    def __str__(self):
        return u'%s - %s' % (self.pid, self.title) or ''

    base_form_class = CoreAdminModelForm
