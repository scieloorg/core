import csv

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import BaseDateRange, CommonControlField
from core.utils.standardizer import clean_xml_tag_content, remove_extra_spaces
from location.models import Location

from . import choices
from .exceptions import (
    OrganizationCreateOrUpdateError,
    OrganizationGetError,
    OrganizationLevelGetError,
    OrganizationTypeGetError,
)

HELP_TEXT_ORGANIZATION = _("Select the standardized organization data")


# =============================================================================
# BASE ORGANIZATION (abstrato)
# =============================================================================

class BaseOrganization(models.Model):
    """
    Classe base abstrata com campos comuns entre Organization e RawOrganization.
    
    Campos:
        - name: nome da organização
        - acronym: sigla/acrônimo
    """
    name = models.CharField(
        _("Name"),
        max_length=255,
        help_text=_("Name of the organization"),
    )
    acronym = models.CharField(
        _("Acronym"),
        max_length=50,
        null=True,
        blank=True,
        help_text=_("Acronym (e.g., USP, FIOCRUZ)"),
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(
                fields=[
                    "name",
                ]
            ),
        ]

    def __str__(self):
        if self.acronym:
            return f"{self.acronym} - {self.name}"
        return self.name


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

    # -------------------------------------------------------------------------
    # Localização (normalizada via FK)
    # -------------------------------------------------------------------------
    
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("Location (country, state, city)"),
    )
    
    # -------------------------------------------------------------------------
    # Identidade visual
    # -------------------------------------------------------------------------
    
    url = models.URLField(
        _("URL"),
        null=True,
        blank=True,
        help_text=_("Official website"),
    )
    logo = models.ImageField(
        _("Logo"),
        null=True,
        blank=True,
        upload_to="organizations/logos/",
    )
    
    # -------------------------------------------------------------------------
    # Classificação
    # -------------------------------------------------------------------------
    
    institution_type = models.ManyToManyField(
        "OrganizationInstitutionType",
        verbose_name=_("Institution Type"),
        blank=True,
        related_name="organizations",
        help_text=_("Types of institution (university, hospital, etc.)"),
    )

    # -------------------------------------------------------------------------
    # Metadados e validação
    # -------------------------------------------------------------------------
    
    source = models.CharField(
        _("Source"),
        max_length=50,
        null=True,
        blank=True,
        default="user_input",
        choices=choices.SOURCE_CHOICES,
        help_text=_("Data source (ror, isni, manual, etc.)"),
    )
    external_id = models.CharField(
        _("External ID"),
        max_length=300,
        null=True,
        blank=True,
        help_text=_("Identifier from external system (e.g., ROR ID)"),
    )
    
    panels = [
        FieldPanel("name"),
        FieldPanel("acronym"),
        AutocompletePanel("location"),
        AutocompletePanel("institution_type"),
        FieldPanel("source"),
        FieldPanel("external_id"),
        FieldPanel("url"),
        FieldPanel("logo"),
    ]
    class Meta:
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")
        unique_together = [("name", "location", "external_id", "source")]  # NOVO
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["source"]),
            models.Index(fields=["external_id"]),
        ]

    @staticmethod
    def autocomplete_custom_queryset_filter(search_term):
        return cls.objects.filter(
            Q(location__country__name__icontains=search_term) | 
            Q(name__icontains=search_term) |
            Q(source=search_term) |
            Q(external_id=search_term)
        )

    def add_source(self, source, save=False):
        self.source = source
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
    
    DEPRECATED: usar BaseOrganizationalLevel em vez disso, pois classe Base não deveria usar CommonControlField

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
        level_1 = clean_xml_tag_content(level_1)
        level_2 = clean_xml_tag_content(level_2)
        level_3 = clean_xml_tag_content(level_3)

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


class BaseOrganizationalLevel(models.Model):
    """
    Classe base para níveis organizacionais hierárquicos (versão 3)
    
    Usado em:
    - OrganizationalLevel
    - RawOrganization.organizational_level
    """

    level_1 = models.CharField(
        _("Level 1"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("e.g., Faculty, School, Institute"),
    )
    level_2 = models.CharField(
        _("Level 2"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("e.g., Department, Division"),
    )
    level_3 = models.CharField(
        _("Level 3"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("e.g., Laboratory, Graduate Program"),
    )

    class Meta:
        abstract = True


# =============================================================================
# ORGANIZATIONAL LEVEL (níveis padronizados)
# =============================================================================

class OrganizationalLevel(BaseOrganizationalLevel, CommonControlField):
    """
    Níveis organizacionais hierárquicos padronizados.
    
    IMPORTANTE: organization é OBRIGATÓRIO.
    Não faz sentido ter níveis sem saber de qual instituição.
    Para dados brutos, usar level_* em RawOrganization.
    
    Usado em:
        - RawOrganization.organizational_level (FK)
        - Programas de pós-graduação, faculdades, departamentos
    
    Exemplo:
        org = Organization.objects.get(name="USP")
        level = OrganizationalLevel.create_or_update(
            user=user,
            organization=org,
            level_1="Faculdade de Medicina",
            level_2="Departamento de Cardiologia",
            level_3="Programa de Pós-Graduação em Ciências Médicas",
        )
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="organizational_levels",
        help_text=_("Parent organization (required)"),
    )
    
    autocomplete_search_field = "level_1"

    class Meta:
        verbose_name = _("Organizational Level")
        verbose_name_plural = _("Organizational Levels")
        unique_together = [("organization", "level_1", "level_2", "level_3")]
        indexes = [
            models.Index(fields=["level_1"]),
            models.Index(fields=["level_2"]),
            models.Index(fields=["level_3"]),
        ]

    def __str__(self):
        parts = [str(self.organization)]
        levels = [lvl for lvl in [self.level_1, self.level_2, self.level_3] if lvl]
        if levels:
            parts.append(" > ".join(levels))
        return " | ".join(parts)

    def autocomplete_label(self):
        return str(self)

    @property
    def levels_display(self):
        """Retorna apenas níveis concatenados (sem organization)."""
        levels = [lvl for lvl in [self.level_1, self.level_2, self.level_3] if lvl]
        return " > ".join(levels) if levels else ""

    panels = [
        AutocompletePanel("organization"),
        FieldPanel("level_1"),
        FieldPanel("level_2"),
        FieldPanel("level_3"),
    ]

    base_form_class = CoreAdminModelForm

    @classmethod
    def get(cls, organization, level_1=None, level_2=None, level_3=None):
        """
        Busca nível organizacional.
        
        Args:
            organization: Organization instance (obrigatório)
            level_1, level_2, level_3: str ou None
        """
        if not organization:
            raise ValueError("OrganizationalLevel.get requires organization")
        
        level_1 = clean_xml_tag_content(level_1)
        level_2 = clean_xml_tag_content(level_2)
        level_3 = clean_xml_tag_content(level_3)
        
        params = {"organization": organization}
        
        if level_1:
            params["level_1__iexact"] = level_1
        else:
            params["level_1__isnull"] = True
            
        if level_2:
            params["level_2__iexact"] = level_2
        else:
            params["level_2__isnull"] = True
            
        if level_3:
            params["level_3__iexact"] = level_3
        else:
            params["level_3__isnull"] = True
        
        try:
            return cls.objects.get(**params)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(**params).first()

    @classmethod
    def create(cls, user, organization, level_1=None, level_2=None, level_3=None):
        """
        Cria nível organizacional.
        """
        if not organization:
            raise ValueError("OrganizationalLevel.create requires organization")
        
        level_1 = clean_xml_tag_content(level_1)
        level_2 = clean_xml_tag_content(level_2)
        level_3 = clean_xml_tag_content(level_3)
        
        try:
            obj = cls(
                creator=user,
                organization=organization,
                level_1=level_1,
                level_2=level_2,
                level_3=level_3,
            )
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(
                organization=organization,
                level_1=level_1,
                level_2=level_2,
                level_3=level_3,
            )

    @classmethod
    def create_or_update(cls, user, organization, level_1=None, level_2=None, level_3=None):
        """
        Cria ou retorna nível existente.
        """
        if not organization:
            raise ValueError("OrganizationalLevel.create_or_update requires organization")
        
        try:
            return cls.get(
                organization=organization,
                level_1=level_1,
                level_2=level_2,
                level_3=level_3,
            )
        except cls.DoesNotExist:
            return cls.create(
                user=user,
                organization=organization,
                level_1=level_1,
                level_2=level_2,
                level_3=level_3,
            )


# =============================================================================
# RAW ORGANIZATION (dados brutos)
# =============================================================================

class RawOrganization(BaseOrganization, BaseOrganizationalLevel, CommonControlField, ClusterableModel):
    """
    Organização com dados brutos (como vieram da fonte).
    
    Armazena dados exatamente como vieram do XML, CSV, API, sem normalização.
    Pode ser vinculado a uma Organization padronizada após processamento.
    
    NÃO contém url/logo - esses dados pertencem à Organization padronizada.
    NÃO contém roles - roles são contextuais (pertencem a Journal, Article, etc.)
    
    Fluxo:
        1. Importação: preenche name, acronym, country, state, city, level_*, source
        2. Normalização: vincula organization e organizational_level
    
    Usado em:
        - journal.models: ?
        - article.models: ?
    
    Exemplo:
        raw = RawOrganization.create_or_update(
            user=user,
            name="Univ. de São Paulo",
            acronym="USP",
            country="Brasil",
            state="SP",
            city="São Paulo",
            level_1="Faculdade de Medicina",
            level_2="Departamento de Cardiologia",
            source="article_xml",
        )
        
        # Após normalização:
        raw.organization = Organization.objects.get(name="Universidade de São Paulo")
        raw.match_status = "manual"
        raw.save()
    """
    # -------------------------------------------------------------------------
    # Original e Nome normalizado
    # -------------------------------------------------------------------------
    
    original = models.CharField(
        _("Original"),
        max_length=300,
        null=True,
        blank=True,
        help_text=_("Original text"),
    )
    normalized_name = models.CharField(
        _("Normalized name"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Normalized name"),
    )

    # -------------------------------------------------------------------------
    # Localização bruta (CharField, como veio da fonte)
    # -------------------------------------------------------------------------
    
    country = models.CharField(
        _("Country"),
        max_length=100,
        null=True,
        blank=True,
        help_text=_("Country as received (e.g., 'Brasil', 'Brazil', 'BR')"),
    )
    state = models.CharField(
        _("State"),
        max_length=100,
        null=True,
        blank=True,
        help_text=_("State/province as received"),
    )
    city = models.CharField(
        _("City"),
        max_length=100,
        null=True,
        blank=True,
        help_text=_("City as received"),
    )
    
    # -------------------------------------------------------------------------
    # Vínculos normalizados (preenchidos após processamento)
    # -------------------------------------------------------------------------
    
    organization = models.ManyToManyField(
        Organization,
        blank=True,
        related_name="raw_organizations",
        verbose_name=_("Organization"),
        help_text=_("Standardized organization (after normalization)"),
    )
    organizational_level = models.ManyToManyField(
        "OrganizationalLevel",
        blank=True,
        related_name="raw_organization_leves",
        verbose_name=_("Organizational Level"),
        help_text=_("Standardized levels (requires organization)"),
    )
    
    # -------------------------------------------------------------------------
    # Metadados
    # -------------------------------------------------------------------------
    
    MATCH_STATUS_CHOICES = [
        ("unmatched", _("Unmatched")),
        ("auto", _("Auto-matched")),
        ("manual", _("Manually matched")),
    ]
    
    match_status = models.CharField(
        _("Match Status"),
        max_length=20,
        choices=MATCH_STATUS_CHOICES,
        default="unmatched",
        help_text=_("Status of link to Organization"),
    )

    # -------------------------------------------------------------------------
    # Configuração
    # -------------------------------------------------------------------------

    @staticmethod
    def autocomplete_custom_queryset_filter(search_term):
        return cls.objects.filter(
            Q(country__icontains=search_term) | 
            Q(original__icontains=search_term)
        )

    class Meta:
        verbose_name = _("Raw Organization")
        verbose_name_plural = _("Raw Organizations")
        unique_together = [("name", "acronym", "country", "state", "city", "level_1", "level_2", "level_3")]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["country"]),
            models.Index(fields=["state"]),
            models.Index(fields=["city"]),
            models.Index(fields=["match_status"]),
        ]

    def __str__(self):
        if self.original:
            return f"{self.original}"
        if self.organization:
            return f"{self.organization}"
        return self.name

    def autocomplete_label(self):
        return f"{self}"

    panels = [
        MultiFieldPanel([
            FieldPanel("original"),
            FieldPanel("normalized_name"),
            FieldPanel("name"),
            FieldPanel("acronym"),
        ], heading=_("Identification")),
        
        MultiFieldPanel([
            FieldPanel("country"),
            FieldPanel("state"),
            FieldPanel("city"),
        ], heading=_("Location (raw)")),
        
        MultiFieldPanel([
            FieldPanel("level_1"),
            FieldPanel("level_2"),
            FieldPanel("level_3"),
        ], heading=_("Organizational Levels (raw)")),
        
        MultiFieldPanel([
            AutocompletePanel("organization"),
            AutocompletePanel("organizational_level"),
            FieldPanel("match_status"),
        ], heading=_("Normalization")),
    ]

    base_form_class = CoreAdminModelForm

    # -------------------------------------------------------------------------
    # Validação
    # -------------------------------------------------------------------------

    def clean(self):
        """Validações de integridade."""
        super().clean()
        
        # organizational_level só pode existir se organization existir
        if self.organizational_level and not self.organization:
            raise ValidationError({
                'organizational_level': _(
                    "Cannot set organizational_level without organization"
                )
            })
        
        # organizational_level deve pertencer à organization
        if (self.organizational_level and self.organization and
            self.organizational_level.organization_id != self.organization_id):
            raise ValidationError({
                'organizational_level': _(
                    "Organizational level must belong to the selected organization"
                )
            })

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def is_matched(self):
        """Indica se está vinculado a Organization."""
        return self.organization_id is not None

    # -------------------------------------------------------------------------
    # Métodos de classe
    # -------------------------------------------------------------------------

    @classmethod
    def get(cls, name, original=None, normalized_name=None, acronym=None, country=None, state=None, city=None, level_1=None, level_2=None, level_3=None):
        """
        Busca registro existente.
        """
        if not name:
            raise ValueError("RawOrganization.get requires name")
        
        original = clean_xml_tag_content(original)
        normalized_name = clean_xml_tag_content(normalized_name)
        name = clean_xml_tag_content(name)
        country = clean_xml_tag_content(country)
        state = clean_xml_tag_content(state)
        city = clean_xml_tag_content(city)
        level_1 = clean_xml_tag_content(level_1)
        level_2 = clean_xml_tag_content(level_2)
        level_3 = clean_xml_tag_content(level_3)
        
        params = {"name__iexact": name}
        
        if original:
            params["original__iexact"] = original
        else:
            params["original__isnull"] = True
            
        if normalized_name:
            params["normalized_name__iexact"] = normalized_name
        else:
            params["normalized_name__isnull"] = True
            
        if country:
            params["country__iexact"] = country
        else:
            params["country__isnull"] = True
            
        if state:
            params["state__iexact"] = state
        else:
            params["state__isnull"] = True
            
        if city:
            params["city__iexact"] = city
        else:
            params["city__isnull"] = True
            
        if level_1:
            params["level_1__iexact"] = level_1
        else:
            params["level_1__isnull"] = True
            
        if level_2:
            params["level_2__iexact"] = level_2
        else:
            params["level_2__isnull"] = True
            
        if level_3:
            params["level_3__iexact"] = level_3
        else:
            params["level_3__isnull"] = True
        
        try:
            return cls.objects.get(**params)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(**params).first()

    @classmethod
    def create(
        cls,
        user,
        name,
        original=None,
        normalized_name=None,
        acronym=None,
        country=None,
        state=None,
        city=None,
        level_1=None,
        level_2=None,
        level_3=None,
        organization=None,
        organizational_level=None,
        match_status=None,
        extra_data=None,
    ):
        """
        Cria novo registro.
        """
        if not name:
            raise ValueError("RawOrganization.create requires name")
        
        try:
            obj = cls(
                creator=user,
                original=clean_xml_tag_content(original),
                name=clean_xml_tag_content(name),
                normalized_name=clean_xml_tag_content(normalized_name),
                acronym=clean_xml_tag_content(acronym),
                country=clean_xml_tag_content(country),
                state=clean_xml_tag_content(state),
                city=clean_xml_tag_content(city),
                level_1=clean_xml_tag_content(level_1),
                level_2=clean_xml_tag_content(level_2),
                level_3=clean_xml_tag_content(level_3),
                organization=organization,
                organizational_level=organizational_level,
                match_status=match_status or "unmatched",
                extra_data=extra_data,
            )
            obj.full_clean()
            obj.save()
            return obj
            
        except IntegrityError:
            return cls.get(
                name=name,
                original=original,
                normalized_name=normalized_name,
                acronym=acronym,
                country=country,
                state=state,
                city=city,
                level_1=level_1,
                level_2=level_2,
                level_3=level_3,
            )

    @classmethod
    def create_or_update(
        cls,
        user,
        name,
        original=None,
        normalized_name=None,
        acronym=None,
        country=None,
        state=None,
        city=None,
        level_1=None,
        level_2=None,
        level_3=None,
        organization=None,
        organizational_level=None,
        match_status=None,
        extra_data=None,
    ):
        """
        Cria ou atualiza registro.
        """
        if not name:
            raise ValueError("RawOrganization.create_or_update requires name")
        
        original = clean_xml_tag_content(original)
        name = clean_xml_tag_content(name)
        normalized_name = clean_xml_tag_content(normalized_name)
        acronym = clean_xml_tag_content(acronym)
        country = clean_xml_tag_content(country)
        state = clean_xml_tag_content(state)
        city = clean_xml_tag_content(city)
        
        try:
            obj = cls.get(
                name=name,
                original=original,
                normalized_name=normalized_name,
                acronym=acronym,
                country=country,
                state=state,
                city=city,
                level_1=level_1,
                level_2=level_2,
                level_3=level_3,
            )
            obj.updated_by = user
            
            # Atualiza campos se fornecidos
            if original:
                obj.original = clean_xml_tag_content(original)
            if level_1:
                obj.level_1 = clean_xml_tag_content(level_1)
            if level_2:
                obj.level_2 = clean_xml_tag_content(level_2)
            if level_3:
                obj.level_3 = clean_xml_tag_content(level_3)
            if organization is not None:
                obj.organization = organization
            if organizational_level is not None:
                obj.organizational_level = organizational_level
            if match_status:
                obj.match_status = match_status
            if extra_data:
                obj.extra_data = extra_data
            
            obj.full_clean()
            obj.save()
            return obj
            
        except cls.DoesNotExist:
            return cls.create(
                user=user,
                name=name,
                original=original,
                normalized_name=normalized_name,
                acronym=acronym,
                country=country,
                state=state,
                city=city,
                level_1=level_1,
                level_2=level_2,
                level_3=level_3,
                organization=organization,
                organizational_level=organizational_level,
                match_status=match_status,
                extra_data=extra_data,
            )

    # -------------------------------------------------------------------------
    # Métodos de instância
    # -------------------------------------------------------------------------

    def link_to_organization(self, user, organization, organizational_level=None, match_status="manual"):
        """
        Vincula a uma Organization padronizada.
        
        Args:
            user: User instance
            organization: Organization instance
            organizational_level: OrganizationalLevel instance (opcional)
            match_status: str - 'auto' ou 'manual'
        """
        self.organization = organization
        self.organizational_level = organizational_level
        self.match_status = match_status
        self.updated_by = user
        self.full_clean()
        self.save()


class BaseOrganizationRole(BaseDateRange):
    # importar em Modelos para InlinePanel e usar como ParentalKey Collection, Journal, Article, etc.
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=HELP_TEXT_ORGANIZATION,
    )
    role = models.CharField(
        _("Role"), max_length=50, choices=choices.ORGANIZATION_ROLES
    )

    panels = [
        AutocompletePanel("organization"),
        FieldPanel("role"),
    ] + BaseDateRange.panels

    class Meta:
        abstract = True
        verbose_name = _("Organization Role")
        verbose_name_plural = _("Organization Roles")

    def __str__(self):
        if self.range:
            return f"{self.organization} - {self.role} ({self.range})"
        return f"{self.organization} - {self.role}"
