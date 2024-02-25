import logging

from django.db import models, IntegrityError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.choices import MONTHS
from core.models import CommonControlField, Gender
from core.forms import CoreAdminModelForm
from core.utils.standardizer import remove_extra_spaces
from institution.models import BaseInstitution
from location.models import Location

from . import choices
from .exceptions import PersonNameCreateError
from .forms import ResearcherForm



class Researcher(CommonControlField):
    """
    Class that represent the Researcher
    """
    person_name = models.ForeignKey("PersonName", on_delete=models.SET_NULL, null=True, blank=True)
    affiliation = models.ForeignKey("Affiliation", on_delete=models.SET_NULL, null=True, blank=True)

    @staticmethod
    def autocomplete_custom_queryset_filter(search_term):
        return Researcher.objects.filter(Q(person_name__fullname__icontains=search_term) | Q(person_name__declared_name__icontains=search_term))

    def autocomplete_label(self):
        return str(self)

    base_form_class = ResearcherForm
    panels = [
        AutocompletePanel("person_name"),
        AutocompletePanel("affiliation"),
    ]

    class Meta:
        unique_together = [("person_name", "affiliation")]
        indexes = [
            models.Index(
                fields=[
                    "person_name",
                ]
            ),
        ]

    @property
    def get_full_name(self):
        return self.person_name.get_full_name if self.person_name is not None else None

    @property
    def orcid(self):
        try:
            for item in ResearcherAKA.objects.filter(
                researcher=self,
                researcher_identifier__source_name__iexact="ORCID",
            ):
                return item.researcher_identifier.identifier
        except Exception as e:
            return None

    @property
    def lattes(self):
        try:
            for item in ResearcherAKA.objects.filter(
                researcher=self,
                researcher_identifier__source_name__iexact="LATTES",
            ):
                return item.researcher_identifier.identifier
        except Exception as e:
            return None

    def __str__(self):
        if self.affiliation:
            return f"{self.person_name} ({self.affiliation})"
        return f"{self.person_name}"

    @classmethod
    def get(
        cls,
        person_name,
        affiliation,
    ):
        try:
            return cls.objects.get(
                person_name=person_name, affiliation=affiliation,
            )
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(
                person_name=person_name, affiliation=affiliation,
            ).first()

    @classmethod
    def create(
        cls,
        user,
        person_name,
        affiliation,
    ):
        try:
            obj = cls()
            obj.creator = user
            obj.person_name = person_name
            obj.affiliation = affiliation
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(person_name, affiliation)

    @classmethod
    def _create_or_update(cls, user, person_name, affiliation):
        try:
            return cls.get(person_name, affiliation)
        except cls.DoesNotExist:
            return cls.create(user, person_name, affiliation)

    @classmethod
    def create_or_update(
        cls,
        user,
        given_names=None,
        last_name=None,
        suffix=None,
        declared_name=None,
        affiliation=None,
        aff_name=None,
        aff_div1=None,
        aff_div2=None,
        aff_city_name=None,
        aff_country_text=None,
        aff_country_acronym=None,
        aff_country_name=None,
        aff_state_text=None,
        aff_state_acronym=None,
        aff_state_name=None,
        location=None,
        lang=None,
        orcid=None,
        lattes=None,
        other_ids=None,
        email=None,
        gender=None,
        gender_identification_status=None,

    ):
        person_name = PersonName.get_or_create(
            user,
            given_names=given_names,
            last_name=last_name,
            suffix=suffix,
            declared_name=declared_name,
            fullname=None,
            gender=gender,
            gender_identification_status=gender_identification_status,
        )

        if not affiliation:
            try:
                location = location or Location.create_or_update(
                    user,
                    country=None,
                    country_name=aff_country_name,
                    country_acron3=None,
                    country_acronym=aff_country_acronym,
                    country_text=aff_country_text,
                    state=None,
                    state_name=aff_state_name,
                    state_acronym=aff_state_acronym,
                    state_text=aff_state_text,
                    city=None,
                    city_name=aff_city_name,
                    lang=lang,
                )
            except Exception as e:
                location = None

        if not affiliation and aff_name:
            affiliation = affiliation or Affiliation.get_or_create(
                user,
                name=aff_name,
                acronym=None,
                level_1=aff_div1,
                level_2=aff_div2,
                level_3=None,
                location=location,
                official=None,
                is_official=None,
                url=None,
                institution_type=None,
            )

        researcher = cls._create_or_update(
            user=user,
            person_name=person_name,
            affiliation=affiliation,
        )

        try:
            ids = other_ids or []
            if orcid:
                orcid = orcid.split("/")[-1]
                ids.append({"identifier": orcid, "source_name": "ORCID"})
            if lattes:
                lattes = lattes.split("/")[-1]
                ids.append({"identifier": lattes, "source_name": "LATTES"})
            if email:
                for email_ in email.replace(",", ";").split(";"):
                    ids.append({"identifier": email_, "source_name": "EMAIL"})

            for id_ in ids:
                # {"identifier": email_, "source_name": "EMAIL"}
                ResearcherAKA.get_or_create(
                    user=user,
                    researcher_identifier=ResearcherIdentifier.get_or_create(
                        user, **id_
                    ),
                    researcher=researcher,
                )
        except Exception as e:
            logging.exception(
                f"Unable to register researcher with ID {person_name} {affiliation} {e}"
            )

        return researcher


class Affiliation(BaseInstitution):
    panels = [
        AutocompletePanel("institution"),
    ]

    base_form_class = CoreAdminModelForm

    create_or_update = BaseInstitution.get_or_create


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
    # nome sem padrão definido
    declared_name = models.CharField(
        _("Declared Name"), max_length=255, blank=True, null=True
    )
    gender = models.ForeignKey(Gender, blank=True, null=True, on_delete=models.SET_NULL)
    gender_identification_status = models.CharField(
        _("Gender identification status"),
        max_length=255,
        choices=choices.GENDER_IDENTIFICATION_STATUS,
        null=True,
        blank=True,
    )

    panels = [
        FieldPanel("declared_name"),
        FieldPanel("given_names"),
        FieldPanel("last_name"),
        FieldPanel("suffix"),
        FieldPanel("fullname"),
        FieldPanel("gender"),
        FieldPanel("gender_identification_status"),
    ]
    base_form_class = CoreAdminModelForm

    class Meta:
        unique_together = [
            (
                "fullname",
                "last_name",
                "given_names",
                "suffix",
            ),
            ("declared_name",),
        ]

        indexes = [
            models.Index(
                fields=[
                    "fullname",
                ]
            ),
            models.Index(
                fields=[
                    "declared_name",
                ]
            ),
        ]

    def __str__(self):
        return self.fullname or self.declared_name

    @staticmethod
    def autocomplete_custom_queryset_filter(search_term):
        return PersonName.objects.filter(
            Q(fullname__icontains=search_term) | Q(declared_name__icontains=search_term)
        )

    def autocomplete_label(self):
        return str(self)

    @property
    def get_full_name(self):
        suffix = self.suffix and f" {self.suffix}"
        return f"{self.last_name}{suffix}, {self.given_names}"

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
        declared_name,
    ):
        if last_name or fullname:
            try:
                return cls.objects.get(
                    fullname__iexact=fullname,
                    last_name__iexact=last_name,
                    given_names__iexact=given_names,
                    suffix__iexact=suffix,
                    declared_name__iexact=declared_name,
                )
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(
                    fullname__iexact=fullname,
                    last_name__iexact=last_name,
                    given_names__iexact=given_names,
                    suffix__iexact=suffix,
                    declared_name__iexact=declared_name,
                ).first()
        raise ValueError("PersonName.get requires fullname or last_names parameters")

    @classmethod
    def _create(
        cls,
        user,
        given_names,
        last_name,
        suffix,
        fullname,
        declared_name,
        gender,
        gender_identification_status,
    ):
        try:
            obj = cls()
            obj.creator = user
            obj.given_names = given_names
            obj.last_name = last_name
            obj.suffix = suffix
            obj.fullname = fullname
            obj.declared_name = declared_name
            obj.gender = gender
            obj.gender_identification_status = gender_identification_status
            obj.save()
        except IntegrityError:
            return cls._get(given_names, last_name, suffix, fullname, declared_name)
        except Exception as e:
            data = dict(
                given_names=given_names,
                last_name=last_name,
                suffix=suffix,
                fullname=fullname,
                declared_name=declared_name,
            )
            raise PersonNameCreateError(f"Unable to create PersonName {data} {e}")

    @classmethod
    def get_or_create(
        cls,
        user,
        given_names,
        last_name,
        suffix,
        fullname,
        declared_name,
        gender,
        gender_identification_status,
    ):
        declared_name = remove_extra_spaces(declared_name)
        given_names = remove_extra_spaces(given_names)
        last_name = remove_extra_spaces(last_name)
        suffix = remove_extra_spaces(suffix)
        fullname = remove_extra_spaces(fullname)
        fullname = fullname or PersonName.join_names(given_names, last_name, suffix)

        try:
            return cls._get(given_names, last_name, suffix, fullname, declared_name)
        except cls.DoesNotExist:
            return cls._create(
                user,
                given_names,
                last_name,
                suffix,
                fullname,
                declared_name,
                gender,
                gender_identification_status,
            )


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
        InlinePanel("researcher_also_known_as"),
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


class ResearcherAKA(CommonControlField, Orderable):
    researcher_identifier = ParentalKey(
        ResearcherIdentifier,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="researcher_also_known_as",
    )
    researcher = models.ForeignKey(
        Researcher, blank=True, null=True, on_delete=models.SET_NULL
    )

    base_form_class = ResearcherForm

    panels = [
        AutocompletePanel("researcher"),
    ]

    @classmethod
    def get(
        cls,
        researcher_identifier,
        researcher,
    ):
        if researcher and researcher_identifier:
            return cls.objects.get(
                researcher=researcher,
                researcher_identifier=researcher_identifier,
            )
        raise ValueError(
            "ResearcherIdentifier.get requires researcher and researcher_identifier"
        )

    @classmethod
    def get(
        cls,
        researcher_identifier,
        researcher,
    ):
        try:
            return cls.objects.get(researcher_identifier=researcher_identifier, researcher=researcher)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(
                researcher_identifier=researcher_identifier,
                researcher=researcher,
            ).first()

    @classmethod
    def create(
        cls,
        user,
        researcher_identifier,
        researcher,
    ):
        try:
            obj = cls()
            obj.creator = user
            obj.researcher_identifier = researcher_identifier
            obj.researcher = researcher
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(researcher_identifier, researcher)

    @classmethod
    def get_or_create(
        cls,
        user,
        researcher_identifier,
        researcher,
    ):
        try:
            return cls.get(researcher_identifier, researcher)
        except cls.DoesNotExist:
            return cls.create(
                user, researcher_identifier, researcher
            )


class InstitutionalAuthor(CommonControlField):
    institutional_author = models.TextField(_("Institutional Author"), blank=True, null=True, unique=True)

    autocomplete_search_field = "institutional_author"

    def autocomplete_label(self):
        return str(self)

    @classmethod
    def get(
        cls,
        name,
    ):
        if not name:
            raise ValueError("InstitutionalAuthor.get requires name paramenter")
        return cls.objects.get(institutional_author__iexact=name)
    
    @classmethod
    def create(
        cls,
        name,
        user,
    ):
        try:
            obj = cls(
                institutional_author=name,
                creator=user,
            )
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(name=name)
    
    @classmethod
    def get_or_create(
        cls,
        name,
        user,
    ):
        try:
            return cls.get(name=name)
        except cls.DoesNotExist:
            return cls.create(name=name, user=user)
    
    def __str__(self):
        return f"{self.institutional_author}"