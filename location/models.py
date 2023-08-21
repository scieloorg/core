from django.db import models
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField


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
    
    panels = [
        FieldPanel("name")
    ]

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")

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
        return str(self)

    panels = [
        FieldPanel("name")
    ]

    class Meta:
        verbose_name = _("Region")
        verbose_name_plural = _("Regions")

    def __unicode__(self):
        return "%s" % self.name

    def __str__(self):
        return "%s" % self.name

    @classmethod
    def get_or_create(cls, user, name=None, acronym=None):
        if name:
            try:
                return cls.objects.get(name__icontains=name)
            except:
                pass

        if acronym:
            try:
                return cls.objects.get(acronym__icontains=acronym)
            except:
                pass

        if name or acronym:
            region = Region()
            region.name = name
            region.acronym = acronym
            region.creator = user
            region.save()

            return region

    base_form_class = CoreAdminModelForm


class State(CommonControlField):
    """
    Represent the list of states

    Fields:
        name
        acronym
    """

    name = models.TextField(_("State name"))
    acronym = models.CharField(_("State Acronym"), max_length=2, null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return str(self)

    panels = [
        FieldPanel("name"),
        FieldPanel("acronym"),
        AutocompletePanel("region")
    ]

    class Meta:
        verbose_name = _("State")
        verbose_name_plural = _("States")

    def __unicode__(self):
        return "%s" % self.name

    def __str__(self):
        return "%s" % self.name

    @classmethod
    def get_or_create(cls, user, name=None, acronym=None):
        if name:
            try:
                return cls.objects.get(name__icontains=name)
            except:
                pass

        if acronym:
            try:
                return cls.objects.get(acronym__icontains=acronym)
            except:
                pass

        if name or acronym:
            state = State()
            state.name = name
            state.acronym = acronym
            state.creator = user
            state.save()

            return state

    base_form_class = CoreAdminModelForm


class Country(CommonControlField):
    """
    Represent the list of Countries

    Fields:
        name
        acronym
    """

    name = models.CharField(_("Country Name"), blank=True, null=True, max_length=255)
    acronym = models.CharField(
        _("Country Acronym"), blank=True, null=True, max_length=255
    )

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return str(self)
    
    panels = [
        FieldPanel("name"),
        FieldPanel("acronym"),
    ]
    
    class Meta:
        verbose_name = _("Country")
        verbose_name_plural = _("Countries")

    def __unicode__(self):
        return "%s" % self.name

    def __str__(self):
        return "%s" % self.name

    @classmethod
    def get_or_create(cls, user, name=None, acronym=None):
        if name:
            try:
                return cls.objects.get(name__icontains=name)
            except:
                pass

        if acronym:
            try:
                return cls.objects.get(acronym__icontains=acronym)
            except:
                pass

        if name or acronym:
            country = Country()
            country.name = name
            country.acronym = acronym
            country.creator = user
            country.save()
            return country

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
    def get_or_create(
        cls, user, location_region, location_country, location_state, location_city
    ):
        # check if exists the location
        try:
            return cls.objects.get(
                region=location_region,
                country=location_country,
                state=location_state,
                city=location_city,
            )
        except:
            location = Location()
            location.region = location_region
            location.country = location_country
            location.state = location_state
            location.city = location_city
            location.creator = user
            location.save()

        return location

    base_form_class = CoreAdminModelForm
