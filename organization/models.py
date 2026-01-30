import csv

from django.apps import apps
from django.db import IntegrityError, models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import BaseHistory, CommonControlField
from core.utils.standardizer import remove_extra_spaces
from location.models import Location

from . import choices
from .exceptions import (
    OrganizationCreateOrUpdateError,
    OrganizationGetError,
    OrganizationLevelGetError,
    OrganizationTypeGetError,
)

HELP_TEXT_ORGANIZATION = _("Select the standardized organization data")


class BaseOrganization(models.Model):
    """
    Classe base para organizações com dados básicos (nome, acrônimo, localização) (versão 2 - atual)

    Usado como base para:
    - organization.models.Organization (implementação concreta)
    - Substitui institution.models.BaseInstitution (versão 1) gradualmente
    - Define padrão para organizações no novo sistema
    """

    name = models.TextField(_("Name"), null=False, blank=False)
    acronym = models.TextField(_("Institution Acronym"), null=True, blank=True)
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=False
    )
    url = models.URLField("url", blank=True, null=True)
    logo = models.ImageField(_("Logo"), blank=True, null=True)

    autocomplete_search_field = "name"

    def __str__(self):
        return f"{self.name} | {self.location}"

    def autocomplete_label(self):
        return str(self)

    class Meta:
        abstract = True

        # é uma classe abstrata, unique_together tem que ser definida nas subclasses
        # unique_together = [
        #     ("name", "acronym", "location"),
        # ]
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

    base_form_class = CoreAdminModelForm

    @classmethod
    def get(
        cls,
        name,
        location,
    ):
        name = remove_extra_spaces(name)
        if not name or not location:
            raise OrganizationGetError("Organization.get requires name and location")

        params = {}
        params["name__iexact"] = name
        params["location"] = location
        try:
            return cls.objects.get(**params)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(**params).first()

    @classmethod
    def create(
        cls,
        user,
        name,
        location,
        acronym=None,
        url=None,
        logo=None,
    ):
        try:
            if not user:
                raise OrganizationCreateOrUpdateError(
                    "User is required to create Organization"
                )

            name = remove_extra_spaces(name)
            if not name or not location:
                raise OrganizationCreateOrUpdateError(
                    "Organization requires name and location"
                )
            obj = cls(
                name=name,
                acronym=acronym,
                location=location,
                url=url,
                logo=logo,
            )
            obj.creator = user
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(name=name, location=location)

    @classmethod
    def create_or_update(
        cls,
        user,
        name,
        location,
        acronym=None,
        logo=None,
        url=None,
    ):

        try:
            obj = cls.get(name=name, location=location)
            obj.acronym = acronym
            obj.url = url
            obj.logo = logo
            obj.save()
            return obj

        except cls.DoesNotExist:
            return cls.create(
                user,
                name=name,
                location=location,
                acronym=acronym,
                url=url,
                logo=logo,
            )


class Organization(BaseOrganization, CommonControlField, ClusterableModel):
    """
    Representa organizações/instituições no sistema atual (versão 2)

    Usado em:
    - researcher.models: NewResearcher.affiliation (ForeignKey)
    - researcher.tasks: criação de afiliações para novos pesquisadores
    - researcher.tests: testes de criação de organizações
    - collection.models: referências para organizações de coleções
    - journal.models: organizações responsáveis por revistas
    - core_settings.tasks/tests: importação de dados de organizações
    - editorialboard.tests: organizações de membros editoriais
    - Substitui institution.models.Institution (versão 1) no novo sistema
    """

    # Novo campo: renomeia institution_type_scielo
    # Manter institution_type_scielo para transição gradual
    institution_type = models.ManyToManyField(
        "OrganizationInstitutionType",
        verbose_name=_("Institution Type"),
        blank=True,
        related_name="organizations_v3",  # diferente do antigo para evitar conflito
        help_text=_("Replaces institution_type_scielo"),
    )

    # futuramente deve ser substituído por data_status (True = validated)
    is_official = models.BooleanField(
        _("Is official"),
        null=True,
        blank=True,
    )
    source = models.CharField(
        _("Source"),
        max_length=50,
        null=True,
        blank=True,
        default="user_input",
        help_text=_(
            "Authority that provided this organization data (e.g., scielo, mec, scimago)"
        ),
        choices=choices.SOURCE_CHOICES,
    )
    data_status = models.CharField(
        _("Data Status"),
        max_length=20,
        choices=choices.DATA_STATUS_CHOICES,
        default="to_evaluate",
        help_text=_("Record data status"),
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("acronym"),
        AutocompletePanel("location"),
        AutocompletePanel("institution_type"),
        FieldPanel("source"),
        FieldPanel("data_status"),
        # FieldPanel("is_official"),
        FieldPanel("url"),
        FieldPanel("logo"),
    ]

    class Meta:
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")
        unique_together = [("name", "acronym", "location")]  # NOVO
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["source"]),
            models.Index(fields=["data_status"]),
        ]

    def add_source(self, source, save=False):
        self.source = source
        if save:
            self.save()

    def add_data_status(self, data_status, save=False):
        self.data_status = data_status
        if save:
            self.save()

    def add_institution_type(self, institution_type_obj, save=False):
        if save:
            # antes de adicionar, salva o objeto principal para garantir integridade
            self.save()
        if institution_type_obj and isinstance(
            institution_type_obj, OrganizationInstitutionType
        ):
            self.institution_type.add(institution_type_obj)


class BaseOrgLevel(CommonControlField):
    """
    Classe base para níveis organizacionais hierárquicos (versão 2)

    Usado em:
    - Criação dinâmica de classes via create_org_level_class()
    - Substitui os campos level_1, level_2, level_3 de institution.models.Institution
    - Permite estrutura hierárquica flexível para organizações
    """

    level_1 = models.TextField(_("Organization Level 1"), null=True, blank=True)
    level_2 = models.TextField(_("Organization Level 2"), null=True, blank=True)
    level_3 = models.TextField(_("Organization Level 3"), null=True, blank=True)

    class Meta:
        abstract = True

    @classmethod
    def get(
        cls,
        organization,
        level_1,
        level_2,
        level_3,
    ):
        if not organization:
            raise OrganizationLevelGetError(
                "OrganizationLevel.get requires organization parameter"
            )

        params = {}
        params["organization"] = organization
        if level_1:
            params["level_1__iexact"] = level_1
        if level_2:
            params["level_2__iexact"] = level_2
        if level_3:
            params["level_3__iexact"] = level_3
        if params:
            try:
                return cls.objects.get(**params)
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(**params).first()

    @classmethod
    def create(
        cls,
        organization,
        level_1,
        level_2,
        level_3,
        user,
    ):
        obj = cls(
            organization=organization,
            level_1=level_1,
            level_2=level_2,
            level_3=level_3,
            creator=user,
        )
        obj.save()
        return obj

    @classmethod
    def create_or_update(
        cls,
        organization,
        level_1,
        level_2,
        level_3,
        user,
    ):
        level_1 = remove_extra_spaces(level_1)
        level_2 = remove_extra_spaces(level_2)
        level_3 = remove_extra_spaces(level_3)

        try:
            return cls.get(
                organization=organization,
                level_1=level_1,
                level_2=level_2,
                level_3=level_3,
            )
        except cls.DoesNotExist:
            return cls.create(
                organization=organization,
                level_1=level_1,
                level_2=level_2,
                level_3=level_3,
                user=user,
            )

    @staticmethod
    def create_org_level_class(app_name, class_name):
        """
        Function to create a dynamic class for Organization Levels.
        """
        model = apps.get_model(app_name, class_name)

        class Meta:
            pass

        attrs = {
            "organization": ParentalKey(
                model,
                related_name="org_level",
                null=True,
                blank=True,
            ),
            "__module__": __name__,
            "Meta": Meta,
        }

        return type(f"OrgLevel{class_name}", (BaseOrgLevel,), attrs)

    def __str__(self):
        data = [level for level in [self.level_1, self.level_2, self.level_3] if level]
        return " | ".join(data)


class OrganizationInstitutionType(CommonControlField):
    """
    Representa tipos de instituição SciELO para o sistema atual (versão 2)

    Usado em:
    - Organization.institution_type_scielo (ManyToMany)
    - organization.tasks: OrganizationInstitutionType para importação
    - Substitui institution.models.InstitutionType (versão 1)
    """

    """
    Representa tipos de instituição SciELO para o sistema atual (versão 2)
    
    Usado em:
    - Organization.institution_type_scielo (ManyToMany)
    - organization.tasks: OrganizationInstitutionType para importação
    - Substitui institution.models.InstitutionType (versão 1)
    """
    name = models.CharField(
        verbose_name=_("Institution Type"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Name of the institution type as defined by the authority"),
    )

    source = models.CharField(
        _("Source"),
        max_length=50,
        null=True,
        blank=True,
        default="unknown",
        help_text=_("Authority that defined this type (e.g., scielo, mec, scimago)"),
    )

    panels = [FieldPanel("name"), FieldPanel("source")]

    class Meta:
        verbose_name = _("Institution Type")
        verbose_name_plural = _("Institution Types")
        unique_together = [("name", "source")]  # MODIFICAR: era só unique=True no name
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["source"]),
        ]

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return str(self)

    def __str__(self):
        return f"{self.name} ({self.source})"

    @classmethod
    def load(cls, user, file_path=None):
        file_path = file_path or "./organization/fixtures/institution_type.csv"
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    if not row:
                        continue
                    name = row[0].strip()
                    if not name:
                        continue
                    try:
                        source = row[1].strip()
                    except IndexError:
                        source = "scielo"
                    cls.create_or_update(
                        name=name,
                        source=source,
                        user=user,
                    )
        except FileNotFoundError:
            pass  # Ou trate conforme a necessidade do sistema

    @classmethod
    def get(cls, name, source="scielo"):
        if not name:
            raise OrganizationTypeGetError(
                "OrganizationInstitutionType.get requires name parameter"
            )
        # Agora busca pela combinação única
        return cls.objects.get(name=name, source=source)

    @classmethod
    def create(cls, name, user, source="scielo"):
        try:
            # Usar get_or_create é mais idiomático para o que você precisa
            obj, created = cls.objects.get_or_create(
                name=name,
                source=source,
                defaults={
                    "creator": user
                },  # assume que creator vem de CommonControlField
            )
            return obj
        except IntegrityError:
            return cls.get(name=name, source=source)

    @classmethod
    def create_or_update(cls, name, user, source="scielo"):
        try:
            return cls.get(name=name, source=source)
        except cls.DoesNotExist:
            return cls.create(name=name, user=user, source=source)
