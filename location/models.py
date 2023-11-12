import csv
import logging
import os

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.fields import RichTextField
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField, Language, TextWithLang


class City(CommonControlField):
    """
    Represent a list of cities

    Fields:
        name
    """

    name = models.TextField(_("Name of the city"), unique=True)

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return str(self)

    panels = [FieldPanel("name")]

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    @classmethod
    def load(cls, user, city_data=None):
        if cls.objects.exists():
            city_data = "./location/fixtures/cities.csv"
            with open(city_data, "r") as fp:
                for line in fp.readlines():
                    name = line.strip()
                    cls.get_or_create(name=name, user=user)

    @classmethod
    def get_or_create(cls, user=None, name=None):
        if name:
            try:
                return cls.objects.get(name=name)
            except cls.DoesNotExist:
                city = City()
                city.name = name
                city.creator = user
                city.save()
                return city

    base_form_class = CoreAdminModelForm


class Region(CommonControlField):
    name = models.TextField(_("Name of the region"), null=True, blank=True)
    acronym = models.CharField(
        _("Region Acronym"), max_length=10, null=True, blank=True
    )

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return f"{self.name or self.acronym}"

    panels = [FieldPanel("name"), FieldPanel("acronym")]

    class Meta:
        verbose_name = _("Region")
        verbose_name_plural = _("Regions")
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

    def __unicode__(self):
        return f"{self.name} ({self.acronym})"

    def __str__(self):
        return f"{self.name} ({self.acronym})"

    @classmethod
    def get_or_create(cls, user=None, name=None, acronym=None):
        return cls.create_or_update(user, name=name, acronym=acronym)

    @classmethod
    def get(cls, name=None, acronym=None):
        if not name and not acronym:
            raise ValueError("Region.get requires name or acronym")
        try:
            return cls.objects.get(
                Q(name__iexact=name) | Q(acronym__iexact=acronym)
            )
        except cls.MultipleObjectsReturned:
            return cls.objects.get(name__iexact=name, acronym__iexact=acronym)

    @classmethod
    def create_or_update(cls, user, name=None, acronym=None):
        try:
            obj = cls.get(name=name, acronym=acronym)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.creator = user

        obj.name = name or obj.name
        obj.acronym = acronym or obj.acronym
        obj.save()

        return obj

    base_form_class = CoreAdminModelForm


class State(CommonControlField):
    """
    Represent the list of states

    Fields:
        name
        acronym
    """

    name = models.TextField(_("State name"), null=True, blank=True)
    acronym = models.CharField(_("State Acronym"), max_length=2, null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return f"{self.acronym or self.name}"

    panels = [FieldPanel("name"), FieldPanel("acronym"), AutocompletePanel("region")]

    class Meta:
        verbose_name = _("State")
        verbose_name_plural = _("States")
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

    def __unicode__(self):
        return f"{self.acronym or self.name}"

    def __str__(self):
        return f"{self.acronym or self.name}"

    @classmethod
    def load(cls, user, state_data=None):
        if state_data or not cls.objects.exists():
            state_data = state_data or "./location/fixtures/states.csv"
            with open(state_data, "r") as csvfile:
                reader = csv.DictReader(
                    csvfile, fieldnames=["name", "acron2", "region"], delimiter=";"
                )
                for row in reader:
                    cls.get_or_create(
                        name=row["name"],
                        acronym=row["acron2"],
                        user=user,
                    )

    @classmethod
    def get_or_create(cls, user, name=None, acronym=None, region=None):
        return cls.create_or_update(user, name=name, acronym=acronym, region=region)

    @classmethod
    def get(cls, name=None, acronym=None):
        if not name and not acronym:
            raise ValueError("State.get requires name or acronym")
        try:
            return cls.objects.get(
                Q(name__iexact=name) | Q(acronym__iexact=acronym)
            )
        except cls.MultipleObjectsReturned:
            return cls.objects.get(name__iexact=name, acronym__iexact=acronym)

    @classmethod
    def create_or_update(cls, user, name=None, acronym=None, region=None):
        try:
            obj = cls.get(name=name, acronym=acronym)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.creator = user

        obj.region = region or obj.region
        obj.name = name or obj.name
        obj.acronym = acronym or obj.acronym
        obj.save()

        return obj

    base_form_class = CoreAdminModelForm


class CountryName(TextWithLang, Orderable):
    country = ParentalKey(
        "Country",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="country_name",
    )

    panels = [FieldPanel("text"), AutocompletePanel("language")]
    base_form_class = CoreAdminModelForm

    class Meta:
        verbose_name = _("Country name")
        verbose_name_plural = _("Country names")
        indexes = [
            models.Index(
                fields=[
                    "language",
                ]
            ),
            models.Index(
                fields=[
                    "text",
                ]
            ),
        ]

    autocomplete_search_filter = "text"

    def autocomplete_label(self):
        return f"{self.text} ({self.language})"

    @property
    def data(self):
        d = {
            "country_name__text": self.text,
            "country_name__language": self.language,
        }

        return d

    def __unicode__(self):
        return f"{self.text} ({self.language})"

    def __str__(self):
        return f"{self.text} ({self.language})"

    @classmethod
    def get_or_create(cls, country, language, text, user=None):
        return cls.create_or_update(user, country, language, text)

    @classmethod
    def get(cls, country, language):
        if not country and not language:
            raise ValueError("CountryName.get requires country or language")
        return cls.objects.get(country=country, language=language)

    @classmethod
    def create_or_update(cls, user, country, language, text):
        try:
            obj = cls.get(country, language)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.creator = user

        obj.country = country or obj.country
        obj.language = language or obj.language
        obj.text = text or obj.text
        obj.save()

        return obj


class Country(CommonControlField, ClusterableModel):
    """
    Represent the list of Countries

    Fields:
        name
        acronym
    """

    name = models.CharField(_("Country Name"), blank=True, null=True, max_length=255)
    acronym = models.CharField(
        _("Country Acronym (2 char)"), blank=True, null=True, max_length=2
    )
    acron3 = models.CharField(
        _("Country Acronym (3 char)"), blank=True, null=True, max_length=3
    )

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return str(self)

    panels = [
        FieldPanel("acronym"),
        FieldPanel("acron3"),
        FieldPanel("name"),
        InlinePanel("country_name", label=_("Country names")),
    ]

    class Meta:
        verbose_name = _("Country")
        verbose_name_plural = _("Countries")
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

    def __unicode__(self):
        return "%s" % self.name

    def __str__(self):
        return "%s" % self.name

    @classmethod
    def load(cls, user):
        # País (pt);País (en);Capital;Código ISO (3 letras);Código ISO (2 letras)
        if cls.objects.count() == 0:
            fieldnames = ["name_pt", "name_en", "Capital", "acron3", "acron2"]
            with open("./location/fixtures/country.csv", newline="") as csvfile:
                reader = csv.DictReader(csvfile, fieldnames=fieldnames, delimiter=";")
                for row in reader:
                    if row["acron2"] == "acron2":
                        continue
                    try:
                        cls.create_or_update(
                            user,
                            name=None,
                            acronym=row["acron2"],
                            acron3=row["acron3"],
                            country_names={"pt": row["name_pt"], "en": row["name_en"]},
                        )
                    except Exception as e:
                        print(f"{e} {row}")
                        raise

    @classmethod
    def get(
        cls,
        name,
        acronym,
        acron3,
    ):
        if any([name, acronym, acron3]):
            return cls.objects.get(Q(name=name) | Q(acronym=acronym) | Q(acron3=acron3))
        raise ValueError("Country.get requires parameters")

    @classmethod
    def create_or_update(
        cls, user, name=None, acronym=None, acron3=None, country_names=None
    ):
        try:
            obj = cls.get(name, acronym, acron3)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.creator = user

        obj.name = name or obj.name
        obj.acronym = acronym or obj.acronym
        obj.acron3 = acron3 or obj.acron3
        obj.save()

        logging.info(country_names)
        logging.info(type(country_names))
        for language, text in (country_names or {}).items():
            logging.info(f"{language} {text}")
            language = Language.get_or_create(code2=language)
            CountryName.get_or_create(
                country=obj, language=language, text=text, user=user
            )
        return obj

    base_form_class = CoreAdminModelForm


class Address(CommonControlField):
    """
    Represent the list of address
    Fields:
        name
    """

    name = models.TextField(_("Address"), blank=True, null=True)
    location = models.ForeignKey(
        "Location",
        verbose_name=_("Address"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return str(self)

    panels = [FieldPanel("name"), AutocompletePanel("location")]

    class Meta:
        verbose_name = _("Address")
        verbose_name_plural = _("Adresses")
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __unicode__(self):
        return "%s" % self.name

    def __str__(self):
        return "%s" % self.name

    @classmethod
    def get_or_create(cls, user, name):
        if name:
            try:
                return cls.objects.get(name=name)
            except:
                address = cls()
                address.name = name
                address.creator = user
                address.save()
                return address

    base_form_class = CoreAdminModelForm


class Location(CommonControlField):
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey(
        City,
        verbose_name=_("City"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    state = models.ForeignKey(
        State,
        verbose_name=_("State"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    country = models.ForeignKey(
        Country,
        verbose_name=_("Country"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    autocomplete_search_field = "country__name"

    def autocomplete_label(self):
        return str(self)

    panels = [
        AutocompletePanel("region"),
        AutocompletePanel("city"),
        AutocompletePanel("state"),
        AutocompletePanel("country"),
    ]

    class Meta:
        verbose_name = _("Location")
        verbose_name_plural = _("Locations")

    def __unicode__(self):
        return "%s | %s | %s" % (self.country, self.state, self.city)

    def __str__(self):
        return "%s | %s | %s" % (self.country, self.state, self.city)

    @classmethod
    def get(
        cls,
        location_region,
        location_country,
        location_state,
        location_city,
    ):
        filters = {}

        if location_region:
            filters["region"] = location_region
        if location_country:
            filters["country"] = location_country
        if location_state:
            filters["state"] = location_state
        if location_city:
            filters["city"] = location_city

        if filters:
            return cls.objects.get(**filters)
        raise ValueError(
            "Location.get requires region, country, city or state parameters"
        )

    @classmethod
    def create_or_update(
        cls,
        user,
        location_region,
        location_country,
        location_state,
        location_city,
    ):
        # check if exists the location
        try:
            location = cls.get(
                location_region, location_country, location_state, location_city
            )
            location.updated_by = user
        except cls.DoesNotExist:
            location = cls()
            location.creator = user

        location.region = location_region or location.region
        location.country = location_country or location.country
        location.state = location_state or location.state
        location.city = location_city or location.city
        location.save()
        return location

    base_form_class = CoreAdminModelForm


class CountryFile(models.Model):
    attachment = models.ForeignKey(
        "wagtaildocs.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    is_valid = models.BooleanField(_("Is valid?"), default=False, blank=True, null=True)
    line_count = models.IntegerField(
        _("Number of lines"), default=0, blank=True, null=True
    )

    def filename(self):
        return os.path.basename(self.attachment.name)

    panels = [FieldPanel("attachment")]
