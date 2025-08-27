import csv
import logging
import os

from django.db import models, IntegrityError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.fields import RichTextField
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField, Language, TextWithLang
from core.utils.standardizer import standardize_name, standardize_code_and_name, remove_extra_spaces


class City(CommonControlField):
    """
    Represent a list of cities

    Fields:
        name
    """

    name = models.TextField(_("Name of the city"), unique=True)

    base_form_class = CoreAdminModelForm
    panels = [FieldPanel("name")]
    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return str(self)

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")
        indexes = [
            models.Index(fields=["name"]),
        ]
        unique_together = [("name",)]

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    @classmethod
    def load(cls, user, file_path=None):
        file_path = file_path or "./location/fixtures/cities.csv"
        with open(file_path, "r") as fp:
            for name in fp.readlines():
                try:
                    cls.get_or_create(name=name, user=user)
                except Exception as e:
                    logging.exception(e)

    @classmethod
    def get_or_create(cls, user=None, name=None):
        try:
            return cls.get(name)
        except cls.DoesNotExist:
            return cls.create(user, name)

    @classmethod
    def get(cls, name):
        name = remove_extra_spaces(name)
        if not name:
            raise ValueError("City.get_or_create requires name")
        try:
            return cls.objects.get(name__iexact=name)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(name__iexact=name).first()

    @classmethod
    def create(cls, user=None, name=None):
        name = remove_extra_spaces(name)
        if not name:
            raise ValueError("City.get_or_create requires name")
        try:
            city = City()
            city.name = name
            city.creator = user
            city.save()
            return city
        except IntegrityError:
            return cls.get(name)

    @staticmethod
    def standardize(text, user=None):
        """
        Returns a dict generator which key is the name of the class and
        the value is the object of the class if user is given
        or name of the city
        """
        standardized_city = standardize_name(text)
        for item in standardized_city:
            if user:
                item = City.get_or_create(user=user, name=item["name"])
            yield {"city": item}


class State(CommonControlField):
    """
    Represent the list of states

    Fields:
        name
        acronym
    """

    name = models.TextField(_("State name"), null=True, blank=True)
    acronym = models.CharField(_("State Acronym"), max_length=2, null=True, blank=True)

    base_form_class = CoreAdminModelForm
    panels = [FieldPanel("name"), FieldPanel("acronym")]

    @staticmethod
    def autocomplete_custom_queryset_filter(search_term):
        return State.objects.filter(
            Q(name__icontains=search_term) | Q(acronym__icontains=search_term)
        )

    def autocomplete_label(self):
        return f"{self.acronym or self.name}"

    class Meta:
        verbose_name = _("State")
        verbose_name_plural = _("States")
        unique_together = [("name", "acronym")]
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
    def load(cls, user, file_path=None):
        file_path = file_path or "./location/fixtures/states.csv"
        with open(file_path, "r") as csvfile:
            rows = csv.DictReader(
                csvfile, fieldnames=["name", "acronym", "region"], delimiter=";"
            )
            for row in rows:
                logging.info(row)
                cls.get_or_create(
                    name=row["name"],
                    acronym=row["acronym"],
                    user=user,
                )

    @classmethod
    def get_or_create(cls, user=None, name=None, acronym=None):
        return cls.create_or_update(user, name=name, acronym=acronym)

    @classmethod
    def get(cls, name=None, acronym=None):
        name = remove_extra_spaces(name)
        acronym = remove_extra_spaces(acronym)
        if name or acronym:
            try:
                return cls.objects.get(name__iexact=name, acronym__iexact=acronym)
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(name__iexact=name, acronym__iexact=acronym).first()
        raise ValueError("State.get requires name or acronym")

    @classmethod
    def create(cls, user, name=None, acronym=None):
        name = remove_extra_spaces(name)
        acronym = remove_extra_spaces(acronym)
        if name or acronym:
            try:
                obj = cls()
                obj.name = name
                obj.acronym = acronym
                obj.creator = user
                obj.save()
                return obj
            except IntegrityError:
                return cls.get(name, acronym)
        raise ValueError("State.create requires name or acronym")

    @classmethod
    def create_or_update(cls, user, name=None, acronym=None):
        name = remove_extra_spaces(name)
        acronym = remove_extra_spaces(acronym)
        try:
            obj = cls.get(name=name, acronym=acronym)
            obj.updated_by = user
            obj.name = name or obj.name
            obj.acronym = acronym or obj.acronym
            obj.save()
        except cls.DoesNotExist:
            obj = cls.create(user, name, acronym)
        return obj

    @staticmethod
    def standardize(text, user=None):
        """
        Returns a dict generator which key is the name of the class and
        the value is the object of the class if user is given
        or dict with code and name
        """
        standardized_state = standardize_code_and_name(text)
        for item in standardized_state:
            if user:
                item = State.create_or_update(
                    user, name=item.get("name"), acronym=item.get("code")
                )
            yield {"state": item}


class CountryName(TextWithLang, Orderable):
    country = ParentalKey(
        "Country",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="country_name",
    )

    base_form_class = CoreAdminModelForm
    panels = [FieldPanel("text"), AutocompletePanel("language")]
    autocomplete_search_filter = "text"

    def autocomplete_label(self):
        return f"{self.text} ({self.language})"

    class Meta:
        verbose_name = _("Country name")
        verbose_name_plural = _("Country names")
        unique_together = [("country", "language")]
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
        try:
            return cls.objects.get(country=country, language=language)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(country=country, language=language).first()

    @classmethod
    def create_or_update(cls, user, country, language, text):
        text = remove_extra_spaces(text)
        try:
            obj = cls.get(country, language)
            obj.updated_by = user
            obj.country = country or obj.country
            obj.language = language or obj.language
            obj.text = text or obj.text
            obj.save()
            return obj
        except cls.DoesNotExist:
            return cls.create(user, country, language, text)

    @classmethod
    def create(cls, user, country, language, text):
        text = remove_extra_spaces(text)
        try:
            obj = cls()
            obj.creator = user
            obj.country = country or obj.country
            obj.language = language or obj.language
            obj.text = text or obj.text
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(country, language)

    @classmethod
    def get_country(cls, name):
        name = remove_extra_spaces(name)
        if name:
            for item in CountryName.objects.filter(text=name).iterator():
                if item.country:
                    return item.country
        raise cls.DoesNotExist(f"CountryName {name} does not exist")


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

    base_form_class = CoreAdminModelForm
    panels = [
        FieldPanel("name"),
        FieldPanel("acronym"),
        FieldPanel("acron3"),
        InlinePanel("country_name", label=_("Country names")),
    ]

    @staticmethod
    def autocomplete_custom_queryset_filter(search_term):
        return Country.objects.filter(
            Q(name__icontains=search_term)
            | Q(acronym__icontains=search_term)
            | Q(acron3__icontains=search_term)
        )

    def autocomplete_label(self):
        return self.name or self.acronym

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
        return self.name or self.acronym

    def __str__(self):
        return self.name or self.acronym

    @classmethod
    def load(cls, user, file_path=None):
        # País (pt);País (en);Capital;Código ISO (3 letras);Código ISO (2 letras)
        fieldnames = ["name_pt", "name_en", "Capital", "acron3", "acron2"]
        file_path = file_path or "./location/fixtures/country.csv"
        with open(file_path, newline="") as csvfile:
            reader = csv.DictReader(csvfile, fieldnames=fieldnames, delimiter=";")
            for row in reader:
                cls.create_or_update(
                    user,
                    name=row["name_en"],
                    acronym=row["acron2"],
                    acron3=row["acron3"],
                    country_names={"pt": row["name_pt"], "en": row["name_en"]},
                )

    @classmethod
    def get(
        cls,
        name,
        acronym=None,
        acron3=None,
    ):
        name = remove_extra_spaces(name)
        acronym = remove_extra_spaces(acronym)
        acron3 = remove_extra_spaces(acron3)

        if acronym:
            return cls.objects.get(acronym=acronym)
        if acron3:
            return cls.objects.get(acron3=acron3)
        if name:
            try:
                return cls.objects.get(name=name)
            except cls.DoesNotExist:
                try:
                    return CountryName.get_country(name)
                except CountryName.DoesNotExist as e:
                    raise cls.DoesNotExist(e)
        raise ValueError("Country.get requires parameters")

    @classmethod
    def create_or_update(
        cls,
        user,
        name=None,
        acronym=None,
        acron3=None,
        country_names=None,
        lang_code2=None,
    ):
        name = remove_extra_spaces(name)
        acronym = remove_extra_spaces(acronym)
        acron3 = remove_extra_spaces(acron3)
        lang_code2 = remove_extra_spaces(lang_code2)

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

        country_names = country_names or {}

        if lang_code2 and name:
            country_names[lang_code2] = name

        for lang_code2, text in country_names.items():
            language = Language.get_or_create(code2=lang_code2)
            CountryName.create_or_update(
                country=obj, language=language, text=text, user=user
            )
        return obj

    @staticmethod
    def standardize(text, user=None):
        """
        Returns a dict generator which key is the name of the class and
        which value is or the object of the class or name + code
        Returns object if user is provided
        """
        standardized_country = standardize_code_and_name(text)
        for item in standardized_country:
            if user:
                item = Country.create_or_update(
                    user,
                    name=item.get("name"),
                    acronym=item.get("code"),
                    acron3=None,
                    country_names=None,
                    lang_code2=None,
                )
            yield {"country": item}


class Location(CommonControlField):
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

    base_form_class = CoreAdminModelForm

    panels = [
        AutocompletePanel("city"),
        AutocompletePanel("state"),
        AutocompletePanel("country"),
    ]

    # autocomplete_search_field = "country__name"
    @staticmethod
    def autocomplete_custom_queryset_filter(search_term):
        return Location.objects.filter(
            Q(city__name__icontains=search_term)
            | Q(state__name__icontains=search_term)
            | Q(country__name__icontains=search_term)
        ).prefetch_related("city", "state", "country")

    def autocomplete_label(self):
        return str(self)

    class Meta:
        verbose_name = _("Location")
        verbose_name_plural = _("Locations")
        unique_together = [("country", "state", "city")]

    def __unicode__(self):
        return f"{self.city}, {self.state}, {self.country}"

    def __str__(self):
        return f"{_('Country')}: {self.country}, {_('State')}: {self.state}, {_('City')}: {self.city}"
    
    @property
    def formatted_location(self):
        parts = []

        if self.city:
            parts.append(self.city.name)
        
        if self.state and self.state.acronym:
            parts.append(self.state.acronym)

        if self.country:
            parts.append(self.country.name)

        return ', '.join(parts)

    @classmethod
    def _get(
        cls,
        country=None,
        state=None,
        city=None,
    ):
        if country or state or city:
            try:
                return cls.objects.get(
                    country=country,
                    state=state,
                    city=city,
                )
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(
                    country=country,
                    state=state,
                    city=city,
                ).first()
        raise ValueError("Location.get requires country or state or city parameters")

    @classmethod
    def _create(
        cls,
        user,
        country=None,
        state=None,
        city=None,
    ):
        # check if exists the location
        try:
            obj = cls()
            obj.creator = user
            obj.country = country or obj.country
            obj.state = state or obj.state
            obj.city = city or obj.city
            obj.save()
            return obj
        except IntegrityError:
            return cls._get(country, state, city)

    @classmethod
    def create_or_update(
        cls,
        user,
        country=None,
        country_name=None,
        country_acron3=None,
        country_acronym=None,
        country_text=None,
        state=None,
        state_name=None,
        state_acronym=None,
        state_text=None,
        city=None,
        city_name=None,
        lang=None,
    ):

        try:
            try:
                if country_text:
                    for item in Country.standardize(country_text, user):
                        country = item.get("country")
                country = country or Country.create_or_update(
                    user,
                    name=country_name,
                    acronym=country_acronym,
                    acron3=country_acron3,
                    country_names=None,
                    lang_code2=lang,
                )
            except Exception as e:
                pass

            try:
                if state_text:
                    for item in State.standardize(state_text, user):
                        state = item.get("state")
                state = state or State.create_or_update(
                    user, name=state_name, acronym=state_acronym)
            except Exception as e:
                pass

            try:
                city = city or City.get_or_create(
                    user, city_name
                )
            except Exception as e:
                pass

            return cls._get(country, state, city)
        except cls.DoesNotExist:
            return cls._create(user, country, state, city)


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
