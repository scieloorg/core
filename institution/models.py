from django.db import models
from django.utils.translation import gettext as _
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField
from location.models import Location

from . import choices


class Institution(CommonControlField, ClusterableModel):
    name = models.TextField(_("Name"), null=True, blank=True)
    institution_type = models.TextField(
        _("Institution Type"), choices=choices.inst_type, null=True, blank=True
    )

    location = models.ForeignKey(
        Location, null=True, blank=True, on_delete=models.SET_NULL
    )

    acronym = models.TextField(_("Institution Acronym"), null=True, blank=True)
    level_1 = models.TextField(_("Organization Level 1"), null=True, blank=True)
    level_2 = models.TextField(_("Organization Level 2"), null=True, blank=True)
    level_3 = models.TextField(_("Organization Level 3"), null=True, blank=True)
    url = models.URLField("url", blank=True, null=True)

    logo = models.ImageField(_("Logo"), blank=True, null=True)

    official = models.ForeignKey(
        "Institution",
        verbose_name=_("Institution"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    is_official = models.CharField(
        _("Is official"),
        null=True,
        blank=True,
        choices=choices.is_official,
        max_length=6,
    )

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return self.name

    panels = [
        FieldPanel("name"),
        FieldPanel("acronym"),
        FieldPanel("institution_type"),
        FieldPanel("location"),
        FieldPanel("level_1"),
        FieldPanel("level_2"),
        FieldPanel("level_3"),
        FieldPanel("url"),
        FieldPanel("logo"),
        AutocompletePanel("official"),
        FieldPanel("is_official"),
    ]

    def __unicode__(self):
        return "%s | %s | %s | %s | %s | %s" % (
            self.name,
            self.acronym,
            self.level_1,
            self.level_2,
            self.level_3,
            self.location,
        )

    def __str__(self):
        return "%s | %s | %s | %s | %s | %s" % (
            self.name,
            self.acronym,
            self.level_1,
            self.level_2,
            self.level_3,
            self.location,
        )

    @property
    def data(self):
        _data = {
            "institution__name": self.name,
            "institution__acronym": self.acronym,
            "institution__level_1": self.level_1,
            "institution__level_2": self.level_2,
            "institution__level_3": self.level_3,
            "institution__url": self.url,
        }
        if self.official:
            _data.update(self.official.data)
        _data.update(
            {
                "institution__is_official": self.is_official,
            }
        )

        return _data

    @classmethod
    def get_or_create(
        cls,
        inst_name,
        inst_acronym,
        level_1,
        level_2,
        level_3,
        location,
        official,
        is_official,
    ):
        # Institution
        # check if exists the institution
        parms = {}
        if inst_name:
            parms["name"] = inst_name
        if inst_acronym:
            parms["acronym"] = inst_acronym
        if location:
            parms["location"] = location
        if level_1:
            parms["level_1"] = level_1
        if level_2:
            parms["level_2"] = level_2
        if level_3:
            parms["level_3"] = level_3

        try:
            return cls.objects.get(**parms)
        except:
            institution = cls()
            institution.name = inst_name
            institution.acronym = inst_acronym
            institution.level_1 = level_1
            institution.level_2 = level_2
            institution.level_3 = level_3
            institution.location = location
            institution.official = official
            institution.is_official = is_official
            institution.save()
        return institution

    base_form_class = CoreAdminModelForm


class InstitutionHistory(models.Model):
    institution = models.ForeignKey(
        "Institution", null=True, blank=True, related_name="+", on_delete=models.CASCADE
    )
    initial_date = models.DateField(_("Initial Date"), null=True, blank=True)
    final_date = models.DateField(_("Final Date"), null=True, blank=True)

    panels = [
        FieldPanel("institution", heading=_("Institution")),
        FieldPanel("initial_date"),
        FieldPanel("final_date"),
    ]

    @classmethod
    def get_or_create(cls, institution, initial_date, final_date):
        histories = cls.objects.filter(
            institution=institution, initial_date=initial_date, final_date=final_date
        )
        try:
            history = histories[0]
        except:
            history = cls()
            history.institution = institution
            history.initial_date = initial_date
            history.final_date = final_date
            history.save()
        return history


class Sponsor(Institution):
    panels = Institution.panels

    base_form_class = CoreAdminModelForm
