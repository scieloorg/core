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
    name = models.TextField(
        verbose_name=_("Institution Type"),
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
