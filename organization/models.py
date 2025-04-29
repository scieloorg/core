import csv

from django.apps import apps
from django.db import models, IntegrityError
from django.utils.translation import gettext as _
from modelcluster.models import ClusterableModel
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from . import choices
from .exceptions import (
    OrganizationTypeGetError, 
    OrganizationCreateOrUpdateError, 
    OrganizationLevelGetError, 
    OrganizationGetError
) 
from core.forms import CoreAdminModelForm
from core.models import CommonControlField
from core.utils.standardizer import remove_extra_spaces
from location.models import Location


class BaseOrganization(CommonControlField, ClusterableModel):
    name = models.TextField(_("Name"), null=False, blank=False)
    acronym = models.TextField(_("Institution Acronym"), null=True, blank=True)
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, null=False, blank=False
    )
    panels = [
        FieldPanel("name"),
        FieldPanel("acronym"),
        AutocompletePanel("location"),
    ]
    autocomplete_search_field = "name"

    def __str__(self):
        return f"{self.name} | {self.location}"

    def autocomplete_label(self):
        return str(self)

    class Meta:
        abstract = True
        unique_together = [
            ("name", "acronym", "location"),
        ]
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
            models.Index(
                fields=[
                    "is_official",
                ]
            ),
        ]

    base_form_class = CoreAdminModelForm

    @classmethod
    def get(
        cls,
        name,
        acronym,
        location,
    ):
        if not name and not location:
            raise OrganizationGetError("Organization.get requires name and location")

        params = {}
        params["name__iexact"] = name
        params["location"] = location

        if acronym:
            params["acronym__iexact"] = acronym

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
        user,
    ):
        try:
            obj = cls(
                name=name,
                acronym=acronym,
                location=location,
                creator=user,
            )
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(name=name, acronym=acronym, location=location)

    @classmethod
    def create_or_update(
        cls,
        name,
        acronym=None,
        location=None,
        user=None,
    ):
        if not name or not location:
            raise OrganizationCreateOrUpdateError("Organization requires name and location")

        name = remove_extra_spaces(name)
        acronym = remove_extra_spaces(acronym)

        try:
            return cls.get(name=name, acronym=acronym, location=location)
        except cls.DoesNotExist:
            return cls.create(
                name=name,
                acronym=acronym,
                location=location,
                user=user,
            )


class Organization(BaseOrganization):
    url = models.URLField("url", blank=True, null=True)
    logo = models.ImageField(_("Logo"), blank=True, null=True)
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
        null=True,
        blank=True,
    )
    is_official = models.BooleanField(
        _("Is official"),
        null=True,
        blank=True,
    )

    panels = BaseOrganization.panels + [
        FieldPanel("url"),
        FieldPanel("logo"),
        FieldPanel("institution_type_mec"),
        AutocompletePanel("institution_type_scielo"),
    ]

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
            name,
            acronym,
            location,
            user,
        )
        obj.url = url or obj.url
        obj.logo = logo or obj.logo
        obj.institution_type_mec = institution_type_mec or obj.institution_type_mec
        obj.is_official = is_official or obj.is_official
        obj.save()
        if institution_type_scielo:
            obj.institution_type_scielo.add(institution_type_scielo)
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
            raise OrganizationLevelGetError("OrganizationLevel.get requires organization parameter")

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
            return cls.get(organization=organization, level_1=level_1, level_2=level_2, level_3=level_3)
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

    panels = [AutocompletePanel("name")]

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
                "OrganizationInstitutionType.get requires name paramenter"
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
