import logging
import re
import sys

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, models
from django.db.models import Q
from django.core.exceptions import NON_FIELD_ERRORS
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.choices import MONTHS
from core.forms import CoreAdminModelForm
from core.models import CommonControlField, Gender
from core.utils.extracts_normalized_email import extracts_normalized_email
from core.utils.standardizer import remove_extra_spaces
from institution.models import BaseInstitution
from location.models import Location
from organization.models import Organization
from tracker.models import UnexpectedEvent

from . import choices
from .exceptions import InvalidOrcidError, PersonNameCreateError
from .forms import ResearcherForm

ORCID_REGEX = re.compile(r'\b(?:https?://)?(?:www\.)?(?:orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[0-9X])\b')


class ResearchNameMixin(models.Model):
    """
    Mixin that contains name-related fields for researchers and common CRUD methods
    """

    given_names = models.CharField(
        _("Given names"), max_length=128, blank=False, null=True
    )
    last_name = models.CharField(_("Last name"), max_length=64, blank=False, null=True)
    suffix = models.CharField(_("Suffix"), max_length=16, blank=True, null=True)
    # nome sem padrão definido ou nome completo
    fullname = models.CharField(_("Full Name"), max_length=255, blank=False, null=True)
    declared_name = models.CharField(
        _("Declared Name"), max_length=255, blank=True, null=True
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.fullname}"

    @staticmethod
    def join_names(given_names, last_name, suffix):
        return " ".join(filter(None, [given_names, last_name, suffix]))

    @classmethod
    def _get(cls, **kwargs):
        """
        Base get method with MultipleObjectsReturned handling.
        Subclasses can override to customize lookup logic.
        """
        try:
            return cls.objects.get(**kwargs)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(**kwargs).first()

    @classmethod
    def _create(cls, user, **kwargs):
        """
        Base create method with IntegrityError handling.
        Subclasses can override to customize creation logic.
        """
        try:
            obj = cls(creator=user, **kwargs)
            obj.save()
            return obj
        except IntegrityError:
            # Try to get the existing object
            return cls._get(**kwargs)

    @classmethod
    def _get_or_create(cls, user, **kwargs):
        """
        Base get_or_create pattern.
        Subclasses can override to customize the logic.
        """
        try:
            return cls._get(**kwargs)
        except cls.DoesNotExist:
            return cls._create(user, **kwargs)


class GenderMixin(models.Model):
    """
    Mixin that contains gender-related fields and common CRUD methods
    """

    gender = models.ForeignKey(Gender, blank=True, null=True, on_delete=models.SET_NULL)
    gender_identification_status = models.CharField(
        _("Gender identification status"),
        max_length=255,
        choices=choices.GENDER_IDENTIFICATION_STATUS,
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True

    @classmethod
    def _get(cls, **kwargs):
        """
        Base get method with MultipleObjectsReturned handling.
        Subclasses can override to customize lookup logic.
        """
        try:
            return cls.objects.get(**kwargs)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(**kwargs).first()

    @classmethod
    def _create(cls, user, **kwargs):
        """
        Base create method with IntegrityError handling.
        Subclasses can override to customize creation logic.
        """
        try:
            obj = cls(creator=user, **kwargs)
            obj.save()
            return obj
        except IntegrityError:
            # Try to get the existing object
            return cls._get(**kwargs)

    @classmethod
    def _get_or_create(cls, user, **kwargs):
        """
        Base get_or_create pattern.
        Subclasses can override to customize the logic.
        """
        try:
            return cls._get(**kwargs)
        except cls.DoesNotExist:
            return cls._create(user, **kwargs)


class Researcher(CommonControlField):
    """
    Class that represent the Researcher
    """

    person_name = models.ForeignKey(
        "PersonName", on_delete=models.SET_NULL, null=True, blank=True
    )
    affiliation = models.ForeignKey(
        "Affiliation", on_delete=models.SET_NULL, null=True, blank=True
    )

    @staticmethod
    def autocomplete_custom_queryset_filter(search_term):
        return Researcher.objects.filter(
            Q(person_name__fullname__icontains=search_term)
            | Q(person_name__declared_name__icontains=search_term)
        )

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
    def get(cls, person_name, affiliation):
        """Get Researcher with MultipleObjectsReturned handling."""
        try:
            return cls.objects.get(person_name=person_name, affiliation=affiliation)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(person_name=person_name, affiliation=affiliation).first()

    @classmethod
    def create(cls, user, person_name, affiliation):
        """Create Researcher with IntegrityError handling."""
        try:
            obj = cls(creator=user, person_name=person_name, affiliation=affiliation)
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(person_name, affiliation)

    @classmethod
    def _create_or_update(cls, user, person_name, affiliation):
        """Internal helper for create_or_update."""
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

        if person_name:
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


class PersonName(ResearchNameMixin, GenderMixin, CommonControlField):
    """
    Class that represent the PersonName
    """

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
        return " ".join(filter(None, [given_names, last_name, suffix]))

    @classmethod
    def _get(cls, given_names, last_name, suffix, fullname, declared_name):
        """Override mixin method to add validation and use case-insensitive lookup."""
        if not (last_name or fullname):
            raise ValueError("PersonName.get requires fullname or last_names parameters")
        
        # Use the inherited _get method from mixin with the lookup fields
        return super(PersonName, cls)._get(
            fullname__iexact=fullname,
            last_name__iexact=last_name,
            given_names__iexact=given_names,
            suffix__iexact=suffix,
            declared_name__iexact=declared_name,
        )

    @classmethod
    def _create(cls, user, given_names, last_name, suffix, fullname, declared_name, gender, gender_identification_status):
        """Override mixin method to add custom error handling."""
        try:
            # Use the inherited _create method from mixin
            return super(PersonName, cls)._create(
                user,
                given_names=given_names,
                last_name=last_name,
                suffix=suffix,
                fullname=fullname,
                declared_name=declared_name,
                gender=gender,
                gender_identification_status=gender_identification_status,
            )
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
        fullname = remove_extra_spaces(fullname) or PersonName.join_names(
            given_names, last_name, suffix
        )

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
    def _get(cls, identifier, source_name):
        """Get ResearcherIdentifier with validation."""
        if not (source_name and identifier):
            raise ValueError("ResearcherIdentifier.get requires source_name and identifier")
        
        try:
            return cls.objects.get(source_name=source_name, identifier=identifier)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(source_name=source_name, identifier=identifier).first()

    @classmethod
    def _create(cls, user, identifier, source_name):
        """Create ResearcherIdentifier with IntegrityError handling."""
        try:
            obj = cls(creator=user, identifier=identifier, source_name=source_name)
            obj.save()
            return obj
        except IntegrityError:
            return cls._get(identifier, source_name)

    @classmethod
    def get_or_create(cls, user, identifier, source_name):
        """Get or create ResearcherIdentifier."""
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
    def get(cls, researcher_identifier, researcher):
        """Get ResearcherAKA with MultipleObjectsReturned handling."""
        try:
            return cls.objects.get(
                researcher_identifier=researcher_identifier,
                researcher=researcher
            )
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(
                researcher_identifier=researcher_identifier,
                researcher=researcher
            ).first()

    @classmethod
    def create(cls, user, researcher_identifier, researcher):
        """Create ResearcherAKA with IntegrityError handling."""
        try:
            obj = cls(
                creator=user,
                researcher_identifier=researcher_identifier,
                researcher=researcher
            )
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(researcher_identifier, researcher)

    @classmethod
    def get_or_create(cls, user, researcher_identifier, researcher):
        """Get or create ResearcherAKA."""
        try:
            return cls.get(researcher_identifier, researcher)
        except cls.DoesNotExist:
            return cls.create(user, researcher_identifier, researcher)


class InstitutionalAuthor(CommonControlField):
    collab = models.CharField(_("Collab"), max_length=255, blank=True, null=True)
    affiliation = models.ForeignKey(
        "Affiliation", on_delete=models.SET_NULL, null=True, blank=True
    )

    autocomplete_search_field = "collab"

    def autocomplete_label(self):
        return str(self)

    class Meta:
        unique_together = [("collab", "affiliation")]

    @classmethod
    def get(cls, collab, affiliation):
        """Get InstitutionalAuthor with validation."""
        if not collab:
            raise ValueError("InstitutionalAuthor.get requires collab paramenter")
        return cls.objects.get(collab__iexact=collab, affiliation=affiliation)

    @classmethod
    def create(cls, collab, affiliation, user):
        """Create InstitutionalAuthor with IntegrityError handling."""
        try:
            obj = cls(collab=collab, affiliation=affiliation, creator=user)
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(collab=collab, affiliation=affiliation)

    @classmethod
    def get_or_create(cls, collab, affiliation, user):
        """Get or create InstitutionalAuthor."""
        try:
            return cls.get(collab=collab, affiliation=affiliation)
        except cls.DoesNotExist:
            return cls.create(collab=collab, affiliation=affiliation, user=user)

    def __str__(self):
        return f"{self.collab}"


class ResearcherOrcid(CommonControlField, ClusterableModel):
    orcid = models.CharField(max_length=64, unique=True, null=True)

    panels = [ 
        FieldPanel("orcid"),
        InlinePanel("researcher_orcid", label="Researcher", classname="collapsed"),
    ]

    def __str__(self):
        return f"{self.orcid}"
    
    def get_fullname_researcher(self):
        """
        Function to display the researcher name(s) in the admin interface.
        """
        if self.researcher_orcid.count() == 1:
            return str(self.researcher_orcid.all().first())
        elif self.researcher_orcid.count() > 1:
            researcher_names = ", ".join(str(researcher) for researcher in self.researcher_orcid.all())
            return f"({researcher_names})"
        return None

    get_fullname_researcher.short_description = "Researcher Name"

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "orcid",
                ]
            ),
        ]

    @classmethod
    def get_by_orcid(cls, orcid):
        """
        Try to find the researcher by the ORCID identifier.
        """
        if not orcid:
            raise ValueError(
                "Researcher.get_by_orcid requires orcid parameter"
            )

        return cls.objects.get(orcid=orcid)

    def clean(self):
        if self.orcid:
            self.validate_orcid(self.orcid)
        return super().clean()

    def save(self, **kwargs):
        self.orcid = self.extract_orcid_number(self.orcid)
        super().save(**kwargs)

    @classmethod
    def get(cls, orcid):
        """Get ResearcherOrcid by orcid."""
        return cls.get_by_orcid(orcid)

    @classmethod
    def create(cls, user, orcid):
        """Create ResearcherOrcid with IntegrityError handling."""
        try:
            obj = cls(creator=user, orcid=orcid)
            obj.save()
            return obj
        except IntegrityError:
            return cls.get_by_orcid(orcid)

    @classmethod
    def get_or_create(cls, user, orcid):
        """Get or create ResearcherOrcid with validation."""
        try:
            cls.validate_orcid(orcid)
            return cls.get_by_orcid(orcid)
        except cls.DoesNotExist:
            return cls.create(user, orcid)
        except (InvalidOrcidError, ValueError) as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "task": "researcher.models.ResearcherOrcid.get_or_create",
                    "data": {'orcid': orcid},
                },
            )

    @staticmethod
    def validate_orcid(orcid):
        """
        Valida um ORCID quanto ao formato e ao dígito verificador (checksum).

        Esta função verifica:
        - Se o identificador informado corresponde a um ORCID válido segundo o regex `ORCID_REGEX`,
          aceitando as formas:
            - "https://orcid.org/0000-0002-1825-0097"
            - "orcid.org/0000-0002-1825-0097"
            - "0000-0002-1825-0097"
        - Se o dígito verificador (checksum) está correto conforme a especificação ORCID (ISO/IEC 7064 mod 11-2).
        
        Parâmetros:
        - orcid (str): O ORCID informado, em qualquer um dos formatos aceitos.

        Retorno:
        - None: Não retorna valor quando a validação é bem-sucedida.

        Exceções:
        - ValidationError: Lançada quando:
            - o formato do ORCID é inválido em relação ao `ORCID_REGEX`; ou
            - o dígito verificador (checksum) é inválido.
        """
        # TODO
        # Request to api to validate the orcid
        # https://pub.orcid.org/v3.0/{orcid}/record
        valid_orcid = ORCID_REGEX.match(orcid)
        if not valid_orcid:
            raise ValidationError({"orcid": f"ORCID {orcid} is not valid"})
        if not ResearcherOrcid.orcid_checksum_is_valid(orcid):
            raise ValidationError({"orcid": f"ORCID {orcid} checksum is not valid"})

    @staticmethod
    def orcid_checksum_is_valid(orcid):
        """
        Verifica o dígito verificador (checksum) de um ORCID.
        
        Parâmetros:
        - orcid (str): O ORCID em qualquer formato aceito (URL completa, domínio + id, ou apenas o id
          no formato 0000-0000-0000-0000).

        Retorno:
        - bool: True se o checksum do ORCID é válido; False caso contrário.
        """
        orcid = ResearcherOrcid.extract_orcid_number(orcid)
        core = orcid.replace("-", "")
        digits, check = core[:-1], core[-1]
        total = 0
        for d in digits:
            total = (total + int(d)) * 2
        remainder = total % 11
        checksum = (12 - remainder) % 11
        expected = 'X' if checksum == 10 else str(checksum)
        return expected == check

    @staticmethod
    def extract_orcid_number(orcid):
        """
        Extract the ORCID number from orcid url.
        """
        return ORCID_REGEX.match(orcid).group(1)


class NewResearcher(ResearchNameMixin, GenderMixin, CommonControlField, ClusterableModel):
    orcid = ParentalKey(
        ResearcherOrcid,
        related_name="researcher_orcid",
        on_delete=models.CASCADE,
        null=True,
    )
    affiliation = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True
    )

    panels = [
        FieldPanel("declared_name"),
        FieldPanel("given_names"),
        FieldPanel("last_name"),
        FieldPanel("suffix"),
        FieldPanel("gender"),
        FieldPanel("gender_identification_status"),
        AutocompletePanel("affiliation"),
        InlinePanel("researcher_ids", label="Researcher IDs", classname="collapsed"),
    ]
    base_form_class = CoreAdminModelForm

    autocomplete_search_field = "fullname"
    
    def autocomplete_label(self):
        return str(self)

    @staticmethod
    def autocomplete_custom_queryset_filter(search_term):
        return NewResearcher.objects.filter(fullname__icontains=search_term).prefetch_related("affiliation", "orcid")

    class Meta:
        unique_together = [
            (
                "orcid",
                "fullname",
                "last_name",
                "given_names",
                "suffix",
                "affiliation",
            ),
            (
                "fullname",
                "last_name",
                "given_names",
                "suffix",
                "affiliation",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "fullname",
                ]
            ),
            models.Index(
                fields=[
                    "orcid",
                ]
            ),
        ]

    def __str__(self):
        orcid = self.orcid.orcid if self.orcid else None
        if orcid:
            return f"{self.fullname} ({orcid})"
        return self.fullname

    def save(self, **kwargs):
        self.fullname = self.join_names(self.given_names, self.last_name, self.suffix)
        super().save(**kwargs)

    @classmethod
    def get(cls, suffix, given_names, last_name, orcid=None, affiliation=None):
        """
        Try to find the researcher by the ORCID identifier or by name and affiliation.
        """
        if not given_names or not last_name:
            raise ValueError("Researcher.get requires given_names, last_name parameters")
        
        fullname = cls.join_names(given_names, last_name, suffix)
        if orcid:
            return cls.objects.get(orcid=orcid, fullname__iexact=fullname)
        return cls.objects.get(fullname__iexact=fullname, affiliation=affiliation)

    @classmethod
    def create(cls, user, given_names, last_name, suffix, affiliation, orcid, gender, gender_identification_status):
        """Create NewResearcher, leveraging mixin's create method."""
        try:
            # Use the inherited _create method from mixin
            return super(NewResearcher, cls)._create(
                user,
                given_names=given_names,
                last_name=last_name,
                suffix=suffix,
                gender=gender,
                gender_identification_status=gender_identification_status,
                orcid=orcid,
                affiliation=affiliation,
            )
        except IntegrityError:
            return cls.get(
                given_names=given_names,
                last_name=last_name,
                affiliation=affiliation,
                suffix=suffix,
                orcid=orcid,
            )

    @classmethod
    def get_or_create(
        cls,
        user,
        given_names,
        last_name,
        suffix,
        affiliation,
        orcid=None,
        gender=None,
        gender_identification_status=None,
    ):
        try:
            obj = cls.get(
                given_names=given_names,
                last_name=last_name,
                suffix=suffix,
                affiliation=affiliation,
                orcid=orcid,
            )
            return obj
        except cls.DoesNotExist:
            obj = cls.create(
                user=user,
                given_names=given_names,
                last_name=last_name,
                suffix=suffix,
                orcid=orcid,
                affiliation=affiliation,
                gender=gender,
                gender_identification_status=gender_identification_status,
            )
            return obj
        except ValueError as e:
            data = dict(
                given_names=given_names,
                last_name=last_name,
                suffix=suffix,
            )
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "task": "researcher.models.get_or_create",
                    "data": data,
                },
            )


class ResearcherIds(CommonControlField):
    """
    Class that represent any id of a researcher
    """

    researcher = ParentalKey(
        NewResearcher, related_name="researcher_ids", null=True, blank=True
    )
    identifier = models.CharField(_("ID"), max_length=64, blank=True, null=True)
    source_name = models.CharField(
        choices=choices.IDENTIFIER_TYPE, max_length=64, blank=True, null=True
    )

    panels = [
        FieldPanel("identifier"),
        FieldPanel("source_name"),
    ]

    base_form_class = ResearcherForm

    @staticmethod
    def autocomplete_custom_queryset_filter(any_value):
        return ResearcherIds.objects.filter(identifier__icontains=any_value).prefetch_related("researcher")

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

    def __str__(self):
        return f"{self.source_name}: {self.identifier}"

    @classmethod
    def get(cls, researcher, identifier, source_name):
        """Get ResearcherIds with validation."""
        if not (researcher and source_name and identifier):
            raise ValueError("ResearcherIdentifier.get requires source_name and identifier")
        return cls.objects.get(
            researcher=researcher,
            source_name=source_name,
            identifier=identifier,
        )

    def clean(self):
        if self.source_name == "EMAIL":
            self.validate_email(self.identifier)
        if self.source_name == "LATTES":
            ...
        return super().clean()

    def save(self, **kwargs):
        if self.source_name == "EMAIL":
            email = extracts_normalized_email(self.identifier)
            self.validate_email(email)
            self.identifier = email
        elif self.source_name == "LATTES":
            self.identifier = self.validate_lattes(self.identifier)
        super().save(**kwargs)

    @classmethod
    def create(cls, user, researcher, identifier, source_name):
        """Create ResearcherIds with error handling."""
        try:
            obj = cls(
                creator=user,
                researcher=researcher,
                identifier=identifier,
                source_name=source_name,
            )
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(researcher, identifier, source_name)
        except ValidationError:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=InvalidOrcidError,
                exc_traceback=exc_traceback,
                detail={
                    "task": "researcher.models.ResearcherIds.create",
                    "identifier": identifier,
                    "source_name": source_name,
                },
            )

    @classmethod
    def get_or_create(cls, user, researcher, identifier, source_name):
        """Get or create ResearcherIds with validation."""
        try:
            if source_name == "EMAIL":
                cls.validate_email(identifier)
            elif source_name == "LATTES":
                cls.validate_lattes(identifier)
            return cls.get(researcher=researcher, identifier=identifier, source_name=source_name)
        except cls.DoesNotExist:
            return cls.create(user=user, researcher=researcher, identifier=identifier, source_name=source_name)

    @staticmethod
    def validate_email(email):
        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError({"identifier": f"Email {email} is not valid"})

    @staticmethod
    def validate_lattes(lattes):
        clean_value = re.sub(r'[\.\-]', '', lattes)
        if not re.fullmatch(r'\d{16}', clean_value):
            raise ValidationError({"identifier": f"Lattes {lattes} is not valid"})

    @staticmethod
    def clean_orcid(orcid):
        return re.sub(r"https?://orcid\.org/", "", orcid).strip("/")
