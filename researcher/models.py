import logging
import sys
import os

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.choices import MONTHS
from core.models import CommonControlField, Gender
from core.forms import CoreAdminModelForm
from institution.models import Institution, BaseHistoryItem
from journal.models import Journal
from tracker.models import UnexpectedEvent

from . import choices
from .forms import ResearcherForm


class PersonName(CommonControlField):
    """
    Class that represent the PersonName
    """

    declared_name = models.CharField(
        _("Declared Name"), max_length=256, blank=True, null=True
    )
    given_names = models.CharField(
        _("Given names"), max_length=128, blank=True, null=True
    )
    last_name = models.CharField(_("Last name"), max_length=128, blank=True, null=True)
    suffix = models.CharField(_("Suffix"), max_length=64, blank=True, null=True)

    panels = [
        FieldPanel("given_names"),
        FieldPanel("last_name"),
        FieldPanel("suffix"),
        FieldPanel("declared_name"),
    ]
    base_form_class = CoreAdminModelForm

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "given_names",
                ]
            ),
            models.Index(
                fields=[
                    "last_name",
                ]
            ),
            models.Index(
                fields=[
                    "declared_name",
                ]
            ),
        ]

    def __unicode__(self):
        return self.get_full_name

    def __str__(self):
        return self.get_full_name

    @staticmethod
    def autocomplete_custom_queryset_filter(search_term):
        return PersonName.objects.filter(
            Q(last_name__icontains=search_term)
            | Q(declared_name__icontains=search_term)
            | Q(given_names__icontain=search_term)
        )

    def autocomplete_label(self):
        return str(self)

    @property
    def get_full_name(self):
        # usado no search_index
        if self.suffix and self.last_name:
            return f"{self.last_name} {self.suffix}, {self.given_names}"
        if self.last_name:
            return f"{self.last_name}, {self.given_names}"
        return self.declared_name

    @classmethod
    def get(
        cls,
        given_names,
        last_name,
        suffix,
        declared_name,
    ):
        if not last_name and not given_names or not declared_name:
            raise ValueError(
                "PersonName.get requires given_names and last_names or declared_name parameters"
            )

        return cls.objects.get(
            given_names__iexact=given_names,
            last_name__iexact=last_name,
            suffix__iexact=suffix,
            declared_name__iexact=declared_name,
        )

    @classmethod
    def create_or_update(
        cls,
        user,
        given_names,
        last_name,
        suffix,
        declared_name,
    ):
        try:
            obj = cls.get(
                given_names=given_names,
                last_name=last_name,
                suffix=suffix,
                declared_name=declared_name,
            )
            obj.updated_by = user or obj.updated_by
        except cls.DoesNotExist:
            obj = cls()
            obj.creator = user

        obj.declared_name = declared_name or obj.declared_name
        obj.given_names = given_names or obj.given_names
        obj.last_name = last_name or obj.last_name
        obj.suffix = suffix or obj.suffix

        if not obj.declared_name:
            obj.declared_name = self.given_names + " " + self.last_name
            if obj.suffix:
                obj.declared_name += " " + obj.suffix
        obj.save()
        return obj


class OrcidModel(CommonControlField):
    orcid = models.CharField(_("ORCID"), max_length=20, blank=True, null=True)
    person_names = models.ManyToManyField(PersonName)

    panels = [
        FieldPanel("orcid"),
        AutocompletePanel("person_names"),
    ]

    base_form_class = CoreAdminModelForm

    autocomplete_search_field = "orcid"

    def autocomplete_label(self):
        return self.orcid

    @property
    def get_full_name(self):
        try:
            return sorted(self.get_full_names)[-1]
        except IndexError:
            return None

    @property
    def get_full_names(self):
        for item in self.person_names.iterator():
            yield item.get_full_name

    @classmethod
    def get_or_create(cls, orcid, user=None):
        try:
            return cls.get(orcid=orcid)
        except cls.DoesNotExist:
            obj = cls()
            obj.orcid = orcid
            obj.save()
            return obj

    @classmethod
    def create_or_update(cls, user, orcid, person_name):
        try:
            obj = cls.get(orcid=orcid)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.creator = user
            obj.orcid = orcid
            obj.save()

        if person_name:
            obj.person_names.add(person_name)
            obj.save()

        return obj


class Researcher(ClusterableModel, CommonControlField):
    """
    Class that represent the Researcher
    """

    person_name = models.ForeignKey(
        PersonName, on_delete=models.SET_NULL, blank=True, null=True
    )
    orcid = models.ForeignKey(
        OrcidModel, on_delete=models.SET_NULL, blank=True, null=True
    )
    lattes = models.URLField(_("Lattes"), max_length=256, blank=True, null=True)
    gender = models.ForeignKey(Gender, blank=True, null=True, on_delete=models.SET_NULL)
    gender_identification_status = models.CharField(
        _("Gender identification status"),
        max_length=16,
        choices=choices.GENDER_IDENTIFICATION_STATUS,
        null=True,
        blank=True,
    )

    autocomplete_search_field = "given_names"

    def autocomplete_label(self):
        return str(self)

    panels = [
        FieldPanel("given_names"),
        FieldPanel("last_name"),
        FieldPanel("declared_name"),
        FieldPanel("suffix"),
        FieldPanel("orcid"),
        FieldPanel("lattes"),
        AutocompletePanel("gender"),
        FieldPanel("gender_identification_status"),
    ]

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "given_names",
                ]
            ),
            models.Index(
                fields=[
                    "last_name",
                ]
            ),
            models.Index(
                fields=[
                    "orcid",
                ]
            ),
            models.Index(
                fields=[
                    "lattes",
                ]
            ),
        ]

    @property
    def get_full_name(self):
        return f"{self.last_name}, {self.given_names}"

    def __unicode__(self):
        return "%s%s, %s (%s)" % (
            self.last_name,
            self.suffix and f" {self.suffix}" or "",
            self.given_names,
            self.orcid,
        )

    def __str__(self):
        return "%s%s, %s (%s)" % (
            self.last_name,
            self.suffix and f" {self.suffix}" or "",
            self.given_names,
            self.orcid,
        )

    @classmethod
    def get(
        cls,
        given_names,
        last_name,
        orcid,
        declared_name,
    ):
        if orcid:
            return cls.objects.get(orcid=orcid)
        elif given_names or last_name:
            return cls.objects.get(
                given_names__iexact=given_names,
                last_name__iexact=last_name,
                orcid__isnull=True,
            )
        elif declared_name:
            return cls.objects.get(declared_name=declared_name)
        raise ValueError(
            "Researcher.get requires orcid, given_names, last_names or declared_name parameters"
        )

    @classmethod
    def create_or_update(
        cls,
        given_names,
        last_name,
        declared_name,
        suffix,
        orcid,
        lattes,
        email,
        institution_name,
        gender=None,
        gender_identification_status=None,
        user=None,
    ):
        try:
            researcher = cls.get(
                given_names=given_names,
                last_name=last_name,
                orcid=orcid,
                declared_name=declared_name,
            )
            researcher.updated_by = user or researcher.updated_by
        except cls.DoesNotExist:
            researcher = cls()
            researcher.creator = user
            researcher.orcid = orcid

        researcher.given_names = given_names or researcher.given_names
        researcher.last_name = last_name or researcher.last_name
        institution = None
        if institution_name:
            try:
                institution = Institution.objects.get(name=institution_name)
            except Institution.DoesNotExist:
                pass

        researcher.declared_name = declared_name or researcher.declared_name
        researcher.suffix = suffix or researcher.suffix
        researcher.lattes = lattes or researcher.lattes
        ## TODO
        ## Criar get_or_create para model gender e GenderIdentificationStatus
        researcher.gender = gender or researcher.gender
        researcher.gender_identification_status = (
            gender_identification_status or researcher.gender_identification_status
        )
        researcher.save()

        if email:
            FieldEmail.objects.create(page=researcher, email=email)
        if institution:
            FieldAffiliation.objects.create(page=researcher, institution=institution)
        return researcher

    panels = [
        FieldPanel("given_names"),
        FieldPanel("last_name"),
        FieldPanel("suffix"),
        FieldPanel("orcid"),
        FieldPanel("lattes"),
        InlinePanel("page_email", label=_("Email")),
        FieldPanel("gender"),
        FieldPanel("gender_identification_status"),
        InlinePanel("affiliation", label=_("Affiliation")),
    ]

    base_form_class = ResearcherForm


class ResearcherEmail(Orderable):
    researcher = ParentalKey(
        Researcher,
        on_delete=models.SET_NULL,
        related_name="researcher_email",
        blank=True,
        null=True,
    )
    email = models.EmailField(_("Email"), max_length=128, blank=True, null=True)

    @classmethod
    def create_or_update(cls, user, researcher, email):
        try:
            obj = cls.objects.get(researcher=researcher)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.researcher = researcher
            obj.creator = user
        obj.email = email
        obj.save()
        return obj

    @classmethod
    def get_researcher(
        cls,
        email,
        person_name,
    ):
        if email and person_name:
            obj = cls.objects.get(
                email,
                researcher__person_name=person_name,
            )
            return obj.researcher
        raise ValueError("Researcher.get_by_email requires email")


class Affiliation(Institution):
    panels = Institution.panels

    base_form_class = CoreAdminModelForm


class AffiliationHistoryItem(BaseHistoryItem):
    institution = models.ForeignKey(
        Affiliation,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )


class AffiliationHistory(Orderable, AffiliationHistoryItem):
    researcher = ParentalKey(
        Researcher,
        on_delete=models.SET_NULL,
        related_name="researcher_affiliation",
        blank=True,
        null=True,
    )

    @classmethod
    def get_researcher(
        cls,
        person_name,
        institutions,
        affiliation_year,
    ):

        if not person_name and not institutions:
            ValueError("AffiliationHistory.get_researcher requires person_name and institutions")

        if affiliation_year is None:
            params = dict(
                initial_year=None,
                final_year=None,
            )
        else:
            params = dict(
                initial_year__lte=affiliation_year,
                final_year__gte=affiliation_year,
            )

        for institution in institutions:
            for item in cls.objects.filter(
                researcher__person_name=person_name,
                institution=institution,
                **params
            ):
                if item.researcher:
                    return item.researcher

        params = dict(
            person_name=person_name,
            institutions=institutions,
            affiliation_year=affiliation_year,
        )
        raise cls.DoesNotExist(
            f"AffiliationHistory does not exist {params}")

    @classmethod
    def create_or_update_history(cls, user, researcher, institutions, affiliation_year):
        # Cria relacionamentos de Researcher com AffiliationHistory
        for institution in institutions or []:
            try:
                obj = cls.create_or_update(
                    institution, user,
                    initial_date=affiliation_year, final_date=affiliation_year)
                obj.researcher = researcher
                obj.save()
            except Exception as exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=exception,
                    exc_traceback=exc_traceback,
                    detail={
                        "operation": "AffiliationHistory.create_or_update_history",
                        "researcher": str(researcher),
                        "institution": str(institution),
                        "affiliation_year": affiliation_year,
                    },
                )
