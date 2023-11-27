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
            | Q(given_names__icontains=search_term)
        )

    def autocomplete_label(self):
        return self.declared_name or f"{self.given_names} {self.last_name} {self.suffix}" 

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

    @staticmethod
    def autocomplete_custom_queryset_filter(any_name):
        return Researcher.objects.filter(
            Q(person_name__last_name__icontains=any_name)
            | Q(person_name__declared_name__icontains=any_name)
            | Q(person_name__given_names__icontains=any_name)
        )

    def autocomplete_label(self):
        return f"{self.get_full_name} {self.orcid and self.orcid.orcid}"

    panels = [
        AutocompletePanel("person_name"),
        AutocompletePanel("orcid"),
        FieldPanel("lattes"),
        AutocompletePanel("gender"),
        FieldPanel("gender_identification_status"),
        InlinePanel("researcher_email", label=_("Email")),
        InlinePanel("researcher_affiliation", label=_("Affiliation")),
    ]

    base_form_class = ResearcherForm

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "lattes",
                ]
            ),
        ]

    @property
    def get_full_name(self):
        return (self.orcid or self.person_name).get_full_name

    def __unicode__(self):
        return self.get_full_name

    def __str__(self):
        return self.get_full_name

    @classmethod
    def get_by_lattes(cls, lattes):
        if lattes:
            return cls.objects.get(lattes=lattes)
        raise ValueError("Researcher.get_by_lattes requires lattes")

    @classmethod
    def get_by_orcid(cls, orcid):
        if orcid:
            return cls.objects.get(orcid__orcid=orcid)
        raise ValueError("Researcher.get_by_orcid requires orcid")

    @classmethod
    def get_by_email(
        cls,
        email,
        person_name,
    ):
        try:
            return ResearcherEmail.get_researcher(
                email,
                person_name,
            )
        except ResearcherEmail.DoesNotExist as e:
            raise Researcher.DoesNotExist(e)
        raise ValueError("Researcher.get_by_email requires email")

    @classmethod
    def get_by_affiliation_data(
        cls,
        person_name,
        institutions,
        affiliation_year,
    ):

        try:
            return AffiliationHistory.get_researcher(
                person_name,
                institutions,
                affiliation_year,
            )
        except AffiliationHistory.DoesNotExist as e:
            raise Researcher.DoesNotExist(e)

    @classmethod
    def get_by_researcher_data(
        cls,
        orcid,
        lattes,
        email,
        person_name,
        institutions,
        affiliation_year=None,
    ):
        try:
            return self.get_by_orcid(orcid)
        except (ValueError, cls.DoesNotExist) as e:
            logging.info(f"Unable to get researcher by orcid {orcid} {type(e)} {e}")
        try:
            return self.get_by_lattes(lattes)
        except (ValueError, cls.DoesNotExist) as e:
            logging.info(f"Unable to get researcher by lattes {lattes} {type(e)} {e}")

        try:
            return self.get_by_email(email, person_name)
        except (ValueError, cls.DoesNotExist) as e:
            logging.info(f"Unable to get researcher by email {email} {type(e)} {e}")

        try:
            return self.get_by_affiliation_data(
                person_name,
                institutions,
                affiliation_year,
            )
        except (ValueError, cls.DoesNotExist) as e:
            logging.info(
                f"Unable to get researcher by affiliation {institutions} {type(e)} {e}"
            )

        try:
            # os registros mais antigos não possuiam affiliation
            return cls.objects.get(
                person_name=person_name,
                orcid__isnull=True,
                lattes__isnull=True,
            )
        except cls.MultipleObjectsReturned as exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=exception,
                exc_traceback=exc_traceback,
                detail={
                    "operation": "Researcher.get_by_researcher_data",
                    "params": dict(
                        orcid=orcid,
                        lattes=lattes,
                        email=email,
                        person_name=str(person_name),
                        affiliation_year=affiliation_year,
                    ),
                },
            )

    @classmethod
    def create_or_update(
        cls,
        given_names=None,
        last_name=None,
        declared_name=None,
        suffix=None,
        orcid=None,
        lattes=None,
        email=None,
        institution_name=None,
        person_name=None,
        affiliation_year=None,
        institutions=None,
        gender=None,
        gender_identification_status=None,
        user=None,
    ):
        params = dict(
            given_names=given_names,
            last_name=last_name,
            declared_name=declared_name,
            suffix=suffix,
            orcid=orcid,
            lattes=lattes,
            email=email,
            institution_name=institution_name,
            person_name=person_name,
            affiliation_year=affiliation_year,
            institutions=institutions,
            gender=gender,
            gender_identification_status=gender_identification_status,
        )
        params = {k: str(v) for k, v in params.items()}
        try:
            if not person_name:
                person_name = PersonName.create_or_update(
                    user,
                    given_names=given_names,
                    last_name=last_name,
                    declared_name=declared_name,
                    suffix=suffix,
                )

            if not institutions and institution_name:
                institution = Institution.create_or_update(
                    inst_name=institution_name,
                    inst_acronym=None,
                    level_1=None,
                    level_2=None,
                    level_3=None,
                    location=None,
                    official=None,
                    is_official=None,
                    url=None,
                    user=user,
                )
                if institution:
                    institutions = [institution]

            try:
                researcher = cls.get_by_researcher_data(
                    orcid,
                    lattes,
                    email,
                    person_name,
                    institutions,
                    affiliation_year,
                )
                researcher.updated_by = user
            except cls.DoesNotExist:
                researcher = cls()
                researcher.creator = user

            researcher.person_name = person_name
            researcher.lattes = lattes or researcher.lattes
            ## TODO
            ## Criar get_or_create para model gender e GenderIdentificationStatus
            researcher.gender = gender or researcher.gender
            researcher.gender_identification_status = (
                gender_identification_status or researcher.gender_identification_status
            )
            researcher.orcid = OrcidModel.create_or_update(
                user,
                orcid,
                person_name,
            )
        except Exception as exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=exception,
                exc_traceback=exc_traceback,
                detail={
                    "operation": "Researcher.create_or_update",
                    "params": params,
                },
            )
            raise exception

        try:
            researcher.save()
        except Exception as exception:
            raise ResearcherCreateOrUpdateError(
                f"Unable to create or update Researcher {params}. Exception {type(e)} {e}"
            )

        # Cria relacionamentos de Researcher com AffiliationHistory
        AffiliationHistory.create_or_update_history(
            user, researcher, institutions, affiliation_year
        )

        # Cria relacionamentos de Researcher com ResearcherEmail
        ResearcherEmail.create_or_update(user, researcher=researcher, email=email)
        return researcher


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
