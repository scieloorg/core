from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.panels import FieldPanel

from core.models import CommonControlField, TextWithLang
from core.forms import CoreAdminModelForm


class Vocabulary(CommonControlField):
    name = models.TextField(_("Vocabulary name"), unique=True)
    acronym = models.CharField(
        _("Vocabulary acronym"), max_length=10, null=True, blank=True
    )

    def __unicode__(self):
        return "%s - %s" % (self.name, self.acronym) or ""

    def __str__(self):
        return "%s - %s" % (self.name, self.acronym) or ""

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "name",
                ]
            ),
            models.Index(
                fields=[
                    "acronym",
                ]
            ),
        ]

    panels = [
        FieldPanel("name"),
        FieldPanel("acronym"),
    ]

    @property
    def data(self):
        d = {
            "vocabulary__name": self.name,
            "vocabulary__acronym": self.acronym,
        }
        return d

    @classmethod
    def get_or_create(cls, name, acronym, user):
        try:
            if name and acronym:
                return cls.objects.get(name=name, acronym=acronym)
            if name:
                return cls.objects.get(name=name)
            if acronym:
                return cls.objects.get(acronym=acronym)
        except cls.DoesNotExist:
            vocabulary = cls()
            vocabulary.name = name
            vocabulary.acronym = acronym
            vocabulary.creator = user
            vocabulary.save()

    base_form_class = CoreAdminModelForm


class Keyword(CommonControlField, TextWithLang):
    vocabulary = models.ForeignKey(
        Vocabulary,
        verbose_name=_("Vocabulary"),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    def __unicode__(self):
        return "%s - %s" % (self.text, self.language) or ""

    def __str__(self):
        return "%s - %s" % (self.text, self.language) or ""

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "text",
                ]
            ),
            models.Index(
                fields=[
                    "language",
                ]
            ),
            models.Index(
                fields=[
                    "vocabulary",
                ]
            ),
        ]

    panels = [
        FieldPanel("text"),
        FieldPanel("language"),
        FieldPanel("vocabulary"),
    ]

    @property
    def data(self):
        d = {
            "keyword__text": self.text,
            "keyword__language": self.language,
            "keyword__vocabulary": self.vocabulary,
        }
        return d

    @classmethod
    def get_or_create(cls, text, language, vocabulary, user):
        try:
            return cls.objects.get(text=text, language=language, vocabulary=vocabulary)
        except cls.DoesNotExist:
            keyword = cls()
            keyword.text = text
            keyword.language = language
            keyword.vocabulary = vocabulary
            keyword.creator = user
            keyword.save()

    base_form_class = CoreAdminModelForm
