from django.db import models
from django.utils.translation import gettext as _
from core.models import CommonControlField
from location.forms import (LocationForm, CityForm, CountryForm, StateForm)
from . import choices


class City(CommonControlField):
    """
    Represent a list of cities

    Fields:
        name
    """

    name = models.CharField(_("Name of the city"), blank=True, null=True, max_length=255)

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")

    def __unicode__(self):
        return u'%s' % self.name

    def __str__(self):
        return u'%s' % self.name

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

    base_form_class = CityForm


class State(CommonControlField):
    """
    Represent the list of states

    Fields:
        name
        acronym
    """

    name = models.CharField(_("State name"), blank=True, null=True, max_length=255)
    acronym = models.CharField(_("State Acronym"), blank=True, null=True, max_length=255)
    region = models.CharField(_("Region"), choices=choices.regions, max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = _("State")
        verbose_name_plural = _("States")

    def __unicode__(self):
        return u'%s' % self.name

    def __str__(self):
        return u'%s' % self.name

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

    base_form_class = StateForm


class Country(CommonControlField):
    """
    Represent the list of Countries

    Fields:
        name
        acronym
    """
    name = models.CharField(_("Country Name"), blank=True, null=True, max_length=255)
    acronym = models.CharField(_("Country Acronym"), blank=True, null=True, max_length=255)

    class Meta:
        verbose_name = _("Country")
        verbose_name_plural = _("Countries")

    def __unicode__(self):
        return u'%s' % self.name

    def __str__(self):
        return u'%s' % self.name

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

    base_form_class = CountryForm


class Location(CommonControlField):

    city = models.ForeignKey(City,
                             verbose_name=_("City"),
                             on_delete=models.CASCADE,
                             null=True,
                             blank=True,
                             )
    state = models.ForeignKey(State,
                              verbose_name=_("State"),
                              on_delete=models.CASCADE,
                              null=True, blank=True,
                              )
    country = models.ForeignKey(Country,
                                verbose_name=_("Country"),
                                on_delete=models.CASCADE,
                                null=True, blank=True,
                                )

    class Meta:
        verbose_name = _("Location")
        verbose_name_plural = _("Locations")

    def __unicode__(self):
        return u'%s | %s | %s' % (self.country, self.state, self.city)

    def __str__(self):
        return u'%s | %s | %s' % (self.country, self.state, self.city)

    @classmethod
    def get_or_create(cls, user, location_country, location_state,
                      location_city):

        # check if exists the location
        try:
            return cls.objects.get(
                country=location_country,
                state=location_state,
                city=location_city)
        except:
            location = Location()
            location.country = location_country
            location.state = location_state
            location.city = location_city
            location.creator = user
            location.save()

        return location

    base_form_class = LocationForm
