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
from core.models import (
    BaseHistory,
    CommonControlField,
    OrganizationNameMixin,
    VisualIdentityMixin,
)
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


class BaseOrganization(OrganizationNameMixin, VisualIdentityMixin, models.Model):
    """
    Base abstract model for organizations.
    
    This class combines OrganizationNameMixin (name, acronym) and VisualIdentityMixin (logo, url).
    Subclasses should add their own location field as needed.
    
    Note: location has been moved from BaseOrganization to concrete implementations.
    """

    base_form_class = CoreAdminModelForm

    class Meta:
        abstract = True

    def __str__(self):
        """
        String representation showing name and location if available.
        
        Note: Checks for location attribute and value to support subclasses
        that may not define a location field, while providing better string
        representation for those that do (like Organization).
        """
        if hasattr(self, 'location') and self.location is not None:
            return f"{self.name} | {self.location}"
        return self.name

    @classmethod
    def get(
        cls,
        name,
        acronym,
        location,
        url=None,
    ):
        if not name or not location:
            raise OrganizationGetError("Organization.get requires name and location")

        params = {}
        params["name__iexact"] = name
        params["location"] = location
        if acronym:
            params["acronym__iexact"] = acronym
        if url:
            params["url"] = url
        try:
            return cls.objects.get(**params)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(**params).first()

    @classmethod
    def create(
        cls,
        name,
        acronym,
        location,
        user=None,
        url=None,
        logo=None,
    ):
        try:
            obj = cls(
                name=name,
                acronym=acronym,
                location=location,
                url=url,
                logo=logo,
            )
            if hasattr(obj, "creator") and user:
                obj.creator = user
            obj.save()
            print(obj)
            return obj
        except IntegrityError:
            return cls.get(name=name, acronym=acronym, location=location)

    def update_logo(obj, user, logo=None):
        update = False
        if logo is not None and obj.logo != logo:
            obj.logo = logo
            update = True
        if update:
            if hasattr(obj, "updated_by") and user:
                obj.updated_by = user
            obj.save()

    def update_url(obj, user, url=None):
        update = False
        if url is not None and obj.url != url:
            obj.url = url
            update = True
        if update:
            if hasattr(obj, "updated_by") and user:
                obj.updated_by = user
            obj.save()

    @classmethod
    def create_or_update(
        cls,
        name,
        acronym=None,
        location=None,
        user=None,
        url=None,
        logo=None,
    ):
        if not name or not location:
            raise OrganizationCreateOrUpdateError(
                "Organization requires name and location"
            )

        name = remove_extra_spaces(name)
        acronym = remove_extra_spaces(acronym)

        try:
            obj = cls.get(name=name, acronym=acronym, location=location)
            obj.update_logo(user, logo)
            obj.update_url(user, url)
            return obj

        except cls.DoesNotExist:
            return cls.create(
                name=name,
                acronym=acronym,
                location=location,
                user=user,
                url=url,
                logo=logo,
            )


class Organization(BaseOrganization, CommonControlField, ClusterableModel):
    """
    Concrete organization model with location and institution type information.
    
    Inherits name and acronym from OrganizationNameMixin,
    and logo and url from VisualIdentityMixin through BaseOrganization.
    """
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=False
    )
    institution_type_mec = models.CharField(
        _("Institution Type (MEC)"),
        choices=choices.inst_type,
        max_length=100,
        null=True,
        blank=True,
    )
    institution_type_scielo = models.ManyToManyField(
        "OrganizationInstitutionType",
        verbose_name=_("Institution Type (SciELO)"),
        blank=True,
    )
    is_official = models.BooleanField(
        _("Is official"),
        null=True,
        blank=True,
    )

    class Meta:
        # Note: unique_together uses fields inherited from mixins
        # (name, acronym from OrganizationNameMixin) plus location field
        unique_together = [
            ("name", "acronym", "location"),
        ]

    panels = [
        FieldPanel("name"),
        FieldPanel("acronym"),
        AutocompletePanel("location"),
        FieldPanel("url"),
        FieldPanel("logo"),
        FieldPanel("institution_type_mec"),
        AutocompletePanel("institution_type_scielo"),
        # FieldPanel("is_official"),
    ]

    @property
    def display_name(self):
        items = []
        if self.name:
            items.append(self.name)
        if self.location:
            items.append(str(self.location))
        return ", ".join(items)

    def update_institutions(
        self,
        user,
        institution_type_mec=None,
        institution_type_scielo=None,
        is_official=None,
    ):
        updated = False

        if (
            institution_type_mec is not None
            and self.institution_type_mec != institution_type_mec
        ):
            self.institution_type_mec = institution_type_mec
            updated = True

        if is_official is not None and self.is_official != is_official:
            self.is_official = is_official
            updated = True

        if updated:
            self.updated_by = user
            self.save()

        if institution_type_scielo is not None:
            if isinstance(institution_type_scielo, list):
                self.institution_type_scielo.set(institution_type_scielo)
            else:
                self.institution_type_scielo.add(institution_type_scielo)

    @classmethod
    def create_or_update(
        cls,
        user,
        name,
        acronym=None,
        location=None,
        url=None,
        logo=None,
        institution_type_mec=None,
        institution_type_scielo=None,
        is_official=None,
    ):

        institution_type_mec = remove_extra_spaces(institution_type_mec)
        obj = super().create_or_update(
            name=name,
            acronym=acronym,
            location=location,
            user=user,
            url=url,
            logo=logo,
        )
        obj.update_institutions(
            user, institution_type_mec, institution_type_scielo, is_official
        )

        return obj


class BaseOrgLevel(CommonControlField):
    level_1 = models.CharField(_("Organization Level 1"), max_length=255, null=True, blank=True)
    level_2 = models.CharField(_("Organization Level 2"), max_length=255, null=True, blank=True)
    level_3 = models.CharField(_("Organization Level 3"), max_length=255, null=True, blank=True)

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
    name = models.CharField(
        verbose_name=_("Institution Type"),
        max_length=100,
        null=True,
        blank=True,
        unique=True,
    )

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return str(self)

    panels = [FieldPanel("name")]

    @classmethod
    def load(cls, user, file_path=None):
        file_path = file_path or "./organization/fixtures/institution_type.csv"
        with open(file_path, "r") as file:
            name = csv.reader(file)
            for n in name:
                cls.create_or_update(
                    name=n[0],
                    user=user,
                )

    @classmethod
    def get(cls, name):
        if not name:
            raise OrganizationTypeGetError(
                "OrganizationInstitutionType.get requires name parameter"
            )
        return cls.objects.get(name=name)

    @classmethod
    def create(
        cls,
        name,
        user,
    ):
        try:
            obj = cls(
                name=name,
                creator=user,
            )
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(name=name)

    @classmethod
    def create_or_update(
        cls,
        name,
        user,
    ):
        try:
            return cls.get(name=name)
        except cls.DoesNotExist:
            return cls.create(name=name, user=user)

    def __str__(self):
        return f"{self.name}"


class NormAffiliation(CommonControlField):
    """
    Represents normalized/standardized organization division data.
    
    This model stores standardized forms of organization division information,
    allowing for consistent representation of organizational hierarchies across
    different affiliations.
    
    Fields:
        organization: Reference to the standardized Organization
        location: Reference to the standardized Location
        level_1: First level of organization division (e.g., Department)
        level_2: Second level of organization division (e.g., Unit)
        level_3: Third level of organization division (e.g., Section)
    """
    organization = models.ForeignKey(
        Organization,
        verbose_name=_("Organization"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("Standardized organization reference"),
    )
    location = models.ForeignKey(
        Location,
        verbose_name=_("Location"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("Standardized location reference"),
    )
    level_1 = models.CharField(
        _("Level 1"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("First level of organization division"),
    )
    level_2 = models.CharField(
        _("Level 2"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Second level of organization division"),
    )
    level_3 = models.CharField(
        _("Level 3"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Third level of organization division"),
    )

    base_form_class = CoreAdminModelForm

    panels = [
        AutocompletePanel("organization"),
        AutocompletePanel("location"),
        FieldPanel("level_1"),
        FieldPanel("level_2"),
        FieldPanel("level_3"),
    ]

    class Meta:
        unique_together = [
            ("organization", "location", "level_1", "level_2", "level_3"),
        ]
        indexes = [
            models.Index(fields=["organization"]),
            models.Index(fields=["location"]),
        ]

    def __str__(self):
        parts = []
        if self.organization:
            parts.append(str(self.organization))
        if self.location:
            parts.append(str(self.location))
        levels = [self.level_1, self.level_2, self.level_3]
        for level in levels:
            if level:
                parts.append(level)
        return " - ".join(parts) if parts else "NormAffiliation"

    @classmethod
    def get(cls, organization=None, location=None, level_1=None, level_2=None, level_3=None):
        """
        Get a normalized affiliation by its identifying fields.
        
        Args:
            organization: Organization instance (optional)
            location: Location instance (optional)
            level_1: First level of division (optional)
            level_2: Second level of division (optional)
            level_3: Third level of division (optional)
            
        Returns:
            NormAffiliation instance
            
        Raises:
            ValueError: If no valid search parameters provided
            cls.DoesNotExist: If no matching instance found
        """
        if not any([organization, location, level_1, level_2, level_3]):
            raise ValueError(
                "NormAffiliation.get requires at least one parameter"
            )
        
        params = {}
        params["organization"] = organization
        params["location"] = location
        params["level_1"] = level_1
        params["level_2"] = level_2
        params["level_3"] = level_3
        
        try:
            return cls.objects.get(**params)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(**params).first()

    @classmethod
    def create(cls, user, organization=None, location=None, level_1=None, level_2=None, level_3=None, **kwargs):
        """
        Create a new normalized affiliation.
        
        Args:
            user: User creating the instance
            organization: Organization instance (optional)
            location: Location instance (optional)
            level_1: First level of division (optional)
            level_2: Second level of division (optional)
            level_3: Third level of division (optional)
            **kwargs: Additional field values
            
        Returns:
            New NormAffiliation instance
        """
        obj = cls()
        obj.organization = organization
        obj.location = location
        obj.level_1 = level_1
        obj.level_2 = level_2
        obj.level_3 = level_3
        
        # Set any additional fields from kwargs
        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        
        if user:
            obj.creator = user
        
        obj.save()
        return obj

    @classmethod
    def create_or_update(cls, user, organization=None, location=None, level_1=None, level_2=None, level_3=None, **kwargs):
        """
        Create a new normalized affiliation or update an existing one.
        
        Lookup strategy:
        Uses cls.get() with all 5 unique_together fields to find an existing record.
        If found, updates the non-unique fields from kwargs.
        If not found, creates a new record.
        
        Args:
            user: User creating/updating the instance
            organization: Organization instance (optional)
            location: Location instance (optional)
            level_1: First level of division (optional)
            level_2: Second level of division (optional)
            level_3: Third level of division (optional)
            **kwargs: Additional field values
            
        Returns:
            NormAffiliation instance (created or updated)
        """
        try:
            # Try to get existing instance using all 5 unique_together fields
            obj = cls.get(
                organization=organization,
                location=location,
                level_1=level_1,
                level_2=level_2,
                level_3=level_3,
            )
            
            # Update other fields from kwargs (not the unique_together fields)
            for key, value in kwargs.items():
                if hasattr(obj, key) and key not in ('organization', 'location', 'level_1', 'level_2', 'level_3'):
                    setattr(obj, key, value)
            
            if user:
                obj.updated_by = user
            
            obj.save()
            return obj
            
        except cls.DoesNotExist:
            # No exact match found - create new
            return cls.create(
                user=user,
                organization=organization,
                location=location,
                level_1=level_1,
                level_2=level_2,
                level_3=level_3,
                **kwargs
            )
