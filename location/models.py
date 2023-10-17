import os

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
        indexes = [
            models.Index(
                fields=[
                    "name"
                ]
            ),                        
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
        return str(self)

    panels = [
        FieldPanel("name"),
        FieldPanel("acronym")
    ]

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

    name = models.TextField(_("State name"), null=True, blank=True)
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
        _("Country Acronym (2 char)"), blank=True, null=True, max_length=2
    )
    acron3 = models.CharField(
        _("Country Acronym (3 char)"), blank=True, null=True, max_length=3
    )
    
    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return str(self)
    
    panels = [
        FieldPanel("name"),
        FieldPanel("acronym"),
        FieldPanel("acron3"),
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
    def get(
        cls,
        name,
        acronym,
        acron3,
    ):
        filters = {}
        if name:
            filters['name'] = name
        if acronym:
            filters['acronym'] = acronym
        if acron3:
            filters['acron3'] = acron3

        if filters:
            return cls.objects.get(**filters)

    @classmethod
    def create_or_update(cls, user, name=None, acronym=None, acron3=None):
        try:
            region = cls.get(name, acronym, acron3)
            region.updated_by = user
        except cls.DoesNotExist:
            region = cls()
            region.creator = user

        region.name = name or region.name
        region.acronym = acronym or region.acronym
        region.acron3 = acron3 or region.acron3
        region.save()
        return region
        

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
    
    panels = [
        FieldPanel("name"),
        AutocompletePanel("location")
    ]

    class Meta:
        verbose_name = _("Address")
        verbose_name_plural = _("Adresses")
        indexes = [
            models.Index(
                fields=[
                    "name"
                ]
            ),                        
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
            filters['region'] = location_region
        if location_country:
            filters['country'] = location_country
        if location_state:
            filters['state'] = location_state
        if location_city:
            filters['city'] = location_city

        if filters:
            return cls.objects.get(**filters)
        raise ValueError("Location.get requires region, country, city or state parameters")

    @classmethod
    def create_or_update(
        cls, user, location_region, location_country, location_state, location_city,
    ):
        # check if exists the location
        try:
            location = cls.get(location_region, location_country, location_state, location_city)
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