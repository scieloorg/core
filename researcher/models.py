import os

from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.choices import MONTHS
from core.models import CommonControlField, Gender
from core.forms import CoreAdminModelForm
from core.utils.standardizer import remove_extra_spaces
from institution.models import Institution, InstitutionHistory
from journal.models import Journal

from . import choices
from .forms import ResearcherForm


class Researcher(ClusterableModel, CommonControlField):
    """
    Class that represent the Researcher
    """

    given_names = models.CharField(
        _("Given names"), max_length=128, blank=True, null=True
    )
    last_name = models.CharField(_("Last name"), max_length=128, blank=True, null=True)
    declared_name = models.CharField(
        _("Declared Name"), max_length=255, blank=True, null=True
    )
    suffix = models.CharField(_("Suffix"), max_length=128, blank=True, null=True)
    orcid = models.TextField(_("ORCID"), blank=True, null=True)
    lattes = models.TextField(_("Lattes"), blank=True, null=True)
    gender = models.ForeignKey(Gender, blank=True, null=True, on_delete=models.SET_NULL)
    gender_identification_status = models.CharField(
        _("Gender identification status"),
        max_length=255,
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


class FieldEmail(Orderable):
    page = ParentalKey(Researcher, on_delete=models.CASCADE, related_name="page_email")
    email = models.EmailField(_("Email"), max_length=128, blank=True, null=True)


class FieldAffiliation(Orderable, InstitutionHistory):
    page = ParentalKey(Researcher, on_delete=models.CASCADE, related_name="affiliation")


class PersonName(CommonControlField):
    """
    Class that represent the PersonName
    """

    given_names = models.CharField(
        _("Given names"), max_length=128, blank=True, null=True
    )
    last_name = models.CharField(_("Last name"), max_length=64, blank=True, null=True)
    suffix = models.CharField(_("Suffix"), max_length=16, blank=True, null=True)
    fullname = models.TextField(_("Full Name"), blank=True, null=True)

    panels = [
        FieldPanel("given_names"),
        FieldPanel("last_name"),
        FieldPanel("suffix"),
        FieldPanel("fullname"),
    ]
    base_form_class = CoreAdminModelForm

    class Meta:
        unique_together = [
            ("fullname", "last_name", "given_names", "suffix", ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "fullname",
                ]
            ),
        ]

    def __str__(self):
        return self.fullname

    @staticmethod
    def autocomplete_custom_queryset_filter(search_term):
        return PersonName.objects.filter(
            fullname__icontains=search_term
        )

    def autocomplete_label(self):
        return self.fullname

    @staticmethod
    def join_names(given_names, last_name, suffix):
        return " ".join(
            [
                remove_extra_spaces(item)
                for item in (given_names, last_name, suffix)
                if remove_extra_spaces(item)
            ]
        )

    @classmethod
    def _get(
        cls,
        given_names,
        last_name,
        suffix,
        fullname,
    ):
        if last_name or fullname:
            try:
                return cls.objects.get(
                    fullname__iexact=fullname,
                    last_name__iexact=last_name,
                    given_names__iexact=given_names,
                    suffix__iexact=suffix,
                )
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(
                    fullname__iexact=fullname,
                    last_name__iexact=last_name,
                    given_names__iexact=given_names,
                    suffix__iexact=suffix,
                ).first()
        raise ValueError(
            "PersonName.get requires fullname or last_names parameters"
        )

    @classmethod
    def _create(
        cls,
        user,
        given_names,
        last_name,
        suffix,
        fullname,
    ):
        try:
            obj = cls()
            obj.creator = user
            obj.given_names = given_names
            obj.last_name = last_name
            obj.suffix = suffix
            obj.fullname = fullname
            obj.save()
        except IntegrityError:
            return cls._get(given_names, last_name, suffix, fullname)
        except Exception as e:
            data = dict(
                given_names=given_names,
                last_name=last_name,
                suffix=suffix,
                fullname=fullname,
            )
            raise PersonNameCreateError(
                f"Unable to create PersonName {data} {e}"
            )

    @classmethod
    def get_or_create(
        cls,
        user,
        given_names,
        last_name,
        suffix,
        fullname,
    ):
        given_names = remove_extra_spaces(given_names)
        last_name = remove_extra_spaces(last_name)
        suffix = remove_extra_spaces(suffix)
        fullname = remove_extra_spaces(fullname)
        fullname = fullname or PersonName.join_names(given_names, last_name, suffix)

        try:
            return cls._get(given_names, last_name, suffix, fullname)
        except cls.DoesNotExist:
            return cls._create(user, given_names, last_name, suffix, fullname)


class ResearcherIdentifier(CommonControlField, ClusterableModel):
    """
    Class that represent the Researcher with any id
    """

    identifier = models.CharField(_("ID"), max_length=64, blank=True, null=True)
    source_name = models.CharField(
        _("Source name"), max_length=64, blank=True, null=True
    )

    panels = [
        FieldPanel("identifier"),
        FieldPanel("source_name"),
        # InlinePanel("researcher_also_known_as"),
    ]

    base_form_class = ResearcherForm

    @staticmethod
    def autocomplete_custom_queryset_filter(any_value):
        return ResearcherIdentifier.objects.filter(identifier__icontains=any_value)

    def autocomplete_label(self):
        return f"{self.identifier} {self.source_name}"

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "identifier",
                ]
            ),
        ]

    @classmethod
    def _get(
        cls,
        identifier,
        source_name,
    ):
        if source_name and identifier:
            try:
                return cls.objects.get(
                    source_name=source_name,
                    identifier=identifier,
                )
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(
                    source_name=source_name,
                    identifier=identifier,
                ).first()
        raise ValueError("ResearcherIdentifier.get requires source_name and identifier")

    @classmethod
    def _create(
        cls,
        user,
        identifier,
        source_name,
    ):
        try:
            obj = cls()
            obj.creator = user
            obj.identifier = identifier
            obj.source_name = source_name
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(identifier, source_name)

    @classmethod
    def get_or_create(
        cls,
        user,
        identifier,
        source_name,
    ):
        try:
            return cls._get(identifier, source_name)
        except cls.DoesNotExist:
            return cls._create(user, identifier, source_name)
