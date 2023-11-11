import json
import logging

from django.db import models
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField, TextWithLang, Language
from core.utils.utils import fetch_data
from . import choices


class CollectionName(TextWithLang):
    autocomplete_search_filter = "text"

    def autocomplete_label(self):
        return str(self)

    @property
    def data(self):
        d = {
            "collection_name__text": self.text,
            "collection_name__language": self.language,
        }

        return d

    def __unicode__(self):
        return "%s (%s)" % (self.text, self.language)

    def __str__(self):
        return "%s (%s)" % (self.text, self.language)

    @classmethod
    def get_or_create(cls, lang, name, user=None):
        try:
            obj = cls.objects.get(language=lang, text=name)
        except cls.DoesNotExist:
            obj = cls()
            obj.language = lang
            obj.text = name
            obj.creator = user
            obj.save()
        return obj


class Collection(CommonControlField):
    acron3 = models.CharField(
        _("Acronym with 3 chars"), max_length=10, null=True, blank=True
    )
    acron2 = models.CharField(
        _("Acronym with 2 chars"), max_length=10, null=True, blank=True
    )
    code = models.CharField(_("Code"), max_length=10, null=True, blank=True)
    domain = models.URLField(_("Domain"), null=True, blank=True)
    name = models.ManyToManyField(
        CollectionName, verbose_name="Collection Name", blank=True
    )
    main_name = models.TextField(_("Main name"), null=True, blank=True)
    status = models.TextField(
        _("Status"), choices=choices.STATUS, null=True, blank=True
    )
    has_analytics = models.BooleanField(_("Has analytics"), null=True, blank=True)
    # Antes era type
    collection_type = models.TextField(
        _("Collection Type"), choices=choices.TYPE, null=True, blank=True
    )
    is_active = models.BooleanField(_("Is active"), null=True, blank=True)
    foundation_date = models.DateField(_("Foundation data"), null=True, blank=True)

    autocomplete_search_field = "main_name"

    def autocomplete_label(self):
        return str(self)

    panels = [
        FieldPanel("acron3"),
        FieldPanel("acron2"),
        FieldPanel("code"),
        FieldPanel("domain"),
        AutocompletePanel("name"),
        FieldPanel("main_name"),
        FieldPanel("status"),
        FieldPanel("has_analytics"),
        FieldPanel("collection_type"),
        FieldPanel("is_active"),
        FieldPanel("foundation_date"),
    ]

    class Meta:
        verbose_name = _("Collection")
        verbose_name_plural = _("Collections")
        indexes = [
            models.Index(
                fields=[
                    "acron3",
                ]
            ),
            models.Index(
                fields=[
                    "acron2",
                ]
            ),
            models.Index(
                fields=[
                    "code",
                ]
            ),
            models.Index(
                fields=[
                    "domain",
                ]
            ),
            models.Index(
                fields=[
                    "main_name",
                ]
            ),
            models.Index(
                fields=[
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "collection_type",
                ]
            ),
        ]

    @property
    def data(self):
        d = {
            "collection__acron3": self.acron3,
            "collection__acron2": self.acron2,
            "collection__code": self.code,
            "collection__domain": self.domain,
            "collection__main_name": self.main_name,
            "collection__status": self.status,
            "collection__has_analytics": self.has_analytics,
            "collection__collection_type": self.collection_type,
            "collection__is_active": self.is_active,
            "collection__is_foundation_date": self.foundation_date,
        }

        if self.name:
            d.update(self.name.data)

        return d

    def __unicode__(self):
        return "%s" % self.main_name or ""

    def __str__(self):
        return "%s" % self.main_name or ""

    base_form_class = CoreAdminModelForm

    @classmethod
    def load(cls, user, collections_data=None):
        if not collections_data:
            collections_data = fetch_data(
                "https://articlemeta.scielo.org/api/v1/collection/identifiers/",
                json=True,
                verify=False,
            )

        for collection_data in collections_data:
            logging.info(collection_data)
            cls.create_or_update(
                user,
                main_name=collection_data.get("original_name"),
                acron2=collection_data.get("acron2"),
                acron3=collection_data.get("acron"),
                code=collection_data.get("code"),
                domain=collection_data.get("domain"),
                names=collection_data.get("name"),
                status=collection_data.get("status"),
                has_analytics=collection_data.get("has_analytics"),
                collection_type=collection_data.get("type"),
                is_active=collection_data.get("is_active"),
            )

    @classmethod
    def create_or_update(
        cls,
        user,
        main_name,
        acron2,
        acron3,
        code,
        domain,
        names,
        status,
        has_analytics,
        collection_type,
        is_active,
    ):
        try:
            obj = cls.objects.get(acron3=acron3)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.acron3 = acron3
            obj.creator = user

        obj.main_name = main_name
        obj.acron2 = acron2
        obj.code = code
        obj.domain = domain
        obj.status = status
        obj.has_analytics = has_analytics
        obj.collection_type = collection_type
        obj.is_active = is_active
        obj.save()
        for language in names:
            lang = Language.get_or_create(code2=language, creator=user)
            obj.name.add(CollectionName.get_or_create(lang, names.get(language), user))
        obj.save()
        logging.info(acron3)
        return obj
