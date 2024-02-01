import logging

from django.db import models
from django.utils.translation import gettext as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField, Language, TextWithLang
from core.utils.utils import fetch_data

from . import choices


class CollectionName(TextWithLang):
    collection = ParentalKey(
        "Collection",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="collection_name",
    )

    panels = [
        AutocompletePanel("language"),
        FieldPanel("text"),
    ]

    @property
    def data(self):
        d = {
            "collection_name__text": self.text,
            "collection_name__language": self.language,
        }

        return d

    def __unicode__(self):
        return self.text

    def __str__(self):
        return self.text

    @classmethod
    def get_or_create(cls, collection, lang, name, user=None):
        try:
            obj = cls.objects.get(collection=collection, language=lang, text=name)
        except cls.DoesNotExist:
            obj = cls()
            obj.collection = collection
            obj.language = lang
            obj.text = name
            obj.creator = user
            obj.save()
        return obj


class Collection(CommonControlField, ClusterableModel):
    acron3 = models.CharField(
        _("Acronym with 3 chars"), max_length=10, null=True, blank=True
    )
    acron2 = models.CharField(
        _("Acronym with 2 chars"), max_length=10, null=True, blank=True
    )
    code = models.CharField(_("Code"), max_length=10, null=True, blank=True)
    domain = models.URLField(_("Domain"), null=True, blank=True)
    main_name = models.TextField(_("Main name"), null=True, blank=True)
    status = models.CharField(
        _("Status"), choices=choices.STATUS, max_length=20, null=True, blank=True
    )
    has_analytics = models.BooleanField(_("Has analytics"), null=True, blank=True)
    # Antes era type
    collection_type = models.CharField(
        _("Collection Type"), choices=choices.TYPE, max_length=20, null=True, blank=True
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
        InlinePanel("collection_name", label=_("Translated names")),
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
            CollectionName.get_or_create(obj, lang, names.get(language), user)
        obj.save()
        logging.info(acron3)
        return obj

    @property
    def name(self):
        return CollectionName.objects.filter(collection=self).iterator()
