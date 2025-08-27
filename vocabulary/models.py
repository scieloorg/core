from django.db import IntegrityError, models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField, TextWithLang


class Vocabulary(CommonControlField):
    name = models.TextField(_("Vocabulary name"), null=True, blank=True)
    acronym = models.CharField(
        _("Vocabulary acronym"), max_length=10, null=True, blank=True
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("acronym"),
    ]
    base_form_class = CoreAdminModelForm

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return str(self)

    def __unicode__(self):
        return self.acronym or self.name or ""

    def __str__(self):
        return self.acronym or self.name or ""

    class Meta:
        unique_together = [("acronym", "name")]
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

    @property
    def data(self):
        d = {
            "vocabulary__name": self.name,
            "vocabulary__acronym": self.acronym,
        }
        return d

    @classmethod
    def load(cls, user, items=None):
        if cls.objects.count() == 0:
            items = items or [
                {"name": "Health Science Descriptors", "acronym": "decs"},
                {"name": "Not defined", "acronym": "nd"},
            ]
            for item in items:
                cls.create_or_update(user, **item)

    @classmethod
    def get(cls, acronym, name=None):
        if not acronym:
            raise ValueError("Vocabulary.get requires acronym")

        if name:
            try:
                return cls.objects.get(acronym=acronym, name=name)
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(acronym=acronym, name=name).first()

        try:
            return cls.objects.get(acronym=acronym)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(acronym=acronym).first()

    @classmethod
    def create(cls, user, acronym=None, name=None):
        try:
            obj = cls()
            obj.name = name
            obj.acronym = acronym
            obj.creator = user
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(acronym, name)

    @classmethod
    def create_or_update(cls, user, acronym=None, name=None):
        try:
            return cls.get(acronym, name)
        except cls.DoesNotExist:
            return cls.create(user, acronym, name)


class Keyword(CommonControlField, TextWithLang):
    html_text = RichTextField(_("Rich Text"), null=True, blank=True)
    vocabulary = models.ForeignKey(
        Vocabulary,
        verbose_name=_("Vocabulary"),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    autocomplete_search_field = "html_text"

    def autocomplete_label(self):
        return str(self)

    panels = [
        FieldPanel("text"),
        FieldPanel("html_text"),
        FieldPanel("language"),
        AutocompletePanel("vocabulary"),
    ]
    base_form_class = CoreAdminModelForm

    class Meta:
        unique_together = [("vocabulary", "language", "text")]
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

    autocomplete_search_field = "text"

    def autocomplete_label(self):
        return str(self.text)

    def __unicode__(self):
        return f"{self.vocabulary} {self.text} {self.language}"

    def __str__(self):
        return f"{self.vocabulary} {self.text} {self.language}"

    @property
    def data(self):
        d = {
            "keyword__text": self.text,
            "keyword__language": self.language,
            "keyword__vocabulary": self.vocabulary,
        }
        return d

    @classmethod
    def create_or_update(cls, user, vocabulary, language, text, html_text):
        if not vocabulary:
            vocabulary = Vocabulary.get(acronym="nd")
        if language and text:
            try:
                obj = cls.get(vocabulary=vocabulary, language=language, text=text)
                return obj.update(user, html_text)
            except cls.DoesNotExist:
                return cls.create(user, vocabulary, language, text, html_text)
        raise ValueError("Keyword.get requires language and text paramenters")
    
    @classmethod
    def get(cls, vocabulary, language, text):
        if vocabulary and language and text:
            try:
                return cls.objects.get(
                    vocabulary=vocabulary, language=language, text=text
                )
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(
                    vocabulary=vocabulary, language=language, text=text
                ).first()

    @classmethod
    def create(cls, user, vocabulary, language, text, html_text):
        try:
            obj = cls()
            obj.text = text
            obj.html_text = html_text
            obj.language = language
            obj.vocabulary = vocabulary
            obj.creator = user
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(vocabulary, language, text)

    def update(self, user, html_text):
        self.html_text = html_text
        self.update_by = user
        self.save()
        return self