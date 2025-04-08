import csv


from django.db import models, IntegrityError
from django.utils.translation import gettext as _
from modelcluster.models import ClusterableModel
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from . import choices
from .exceptions import OrganizationTypeGetError
from core.forms import CoreAdminModelForm
from core.models import CommonControlField
from core.utils.standardizer import remove_extra_spaces
from location.models import Location


class BaseOrganization(CommonControlField, ClusterableModel):
    name = models.TextField(_("Name"), null=True, blank=True)
    acronym = models.TextField(_("Institution Acronym"), null=True, blank=True)
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
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_official = models.BooleanField(
        _("Is official"),
        null=True,
        blank=True,
    )
    panels = [
        FieldPanel("name"),
        FieldPanel("acronym"),
        FieldPanel("url"),
        FieldPanel("logo"),
        FieldPanel("institution_type_mec"),
        AutocompletePanel("location"),
        AutocompletePanel("institution_type_scielo"),
        InlinePanel("org_level", max_num=1, label="Organization Level"),
        FieldPanel("is_official"),
    ]
    autocomplete_search_field = "name"

    def __str__(self):
        if self.org_level.exists():
            return f"{self.name} | {str(self.org_level.first())}"
        return f"{self.name}"

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
        params = {}
        if name:
            params["name__iexact"] = name
        if acronym:
            params["acronym__iexact"] = acronym
        if location:
            params["location"] = location
        if params:
            try:
                return cls.objects.get(**params)
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(**params).first()

    @classmethod
    def create(
        cls,
        name,
        acronym,
        url,
        logo,
        institution_type_mec,
        institution_type_scielo,
        location,
        is_official,
        level_1,
        level_2,
        level_3,
        user,
    ):
        try:
            obj = cls(
                name=name,
                acronym=acronym,
                url=url,
                logo=logo,
                institution_type_mec=institution_type_mec,
                location=location,
                is_official=is_official,
                creator=user,
            )
            obj.save()
            if institution_type_scielo:
                obj.institution_type_scielo.add(institution_type_scielo)
    
            if level_1 or level_2 or level_3:
                org_level_model = cls.get_org_level_model()
                org_level_model.objects.create(
                    organization=obj,
                    level_1=level_1,
                    level_2=level_2,
                    level_3=level_3,
                )
            return obj
        except IntegrityError:
            return cls.get(name=name, acronym=acronym, location=location)

    @classmethod
    def create_or_update(
        cls,
        name,
        acronym=None,
        location=None,
        url=None,
        logo=None,
        level_1=None,
        level_2=None,
        level_3=None,
        institution_type_mec=None,
        institution_type_scielo=None,
        is_official=None,
        user=None,
    ):
        name = remove_extra_spaces(name)
        acronym = remove_extra_spaces(acronym)
        level_1 = remove_extra_spaces(level_1)
        level_2 = remove_extra_spaces(level_2)
        level_3 = remove_extra_spaces(level_3)
        institution_type_mec = remove_extra_spaces(institution_type_mec)
        try:
            return cls.get(name=name, acronym=acronym, location=location)
        except cls.DoesNotExist:
            return cls.create(
                name=name,
                acronym=acronym,
                url=url,
                logo=logo,
                institution_type_mec=institution_type_mec,
                institution_type_scielo=institution_type_scielo,
                location=location,
                is_official=is_official,
                level_1=level_1,
                level_2=level_2,
                level_3=level_3,
                user=user,
            )


# Dynamic OrgLevel class creation
def create_org_level_class(org_class_name):
    class Meta:
        pass

    attrs = {
        "organization": ParentalKey(
            org_class_name,
            related_name="org_level",
            null=True,
            blank=True,
        ),
        "__module__": __name__,
        "Meta": Meta,
    }
    return type(f"OrgLevel{org_class_name}", (BaseOrgLevel,), attrs)


class BaseOrgLevel(CommonControlField):
    level_1 = models.TextField(_("Organization Level 1"), null=True, blank=True)
    level_2 = models.TextField(_("Organization Level 2"), null=True, blank=True)
    level_3 = models.TextField(_("Organization Level 3"), null=True, blank=True)

    class Meta:
        abstract = True

    @classmethod
    def get(
        cls,
        level_1,
        level_2,
        level_3,
    ):
        params = {}
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

    def __str__(self):
        data = [level for level in [self.level_1, self.level_2, self.level_3] if level]
        return " | ".join(data)


class OrganizationPublisher(BaseOrganization):
    @classmethod
    def get_org_level_model(cls):
        return OrgLevelPublisher


class OrganizationOwner(BaseOrganization):
    @classmethod
    def get_org_level_model(cls):
        return OrgLevelOwner


class OrganizationSponsor(BaseOrganization):
    @classmethod
    def get_org_level_model(cls):
        return OrgLevelSponsor


class OrganizationCopyrightHolder(BaseOrganization):
    @classmethod
    def get_org_level_model(cls):
        return OrgLevelCopyright


class OrganizationAffiliation(BaseOrganization):
    @classmethod
    def get_org_level_model(cls):
        return OrgLevelAffiliation


OrgLevelPublisher = create_org_level_class("OrganizationPublisher")
OrgLevelOwner = create_org_level_class("OrganizationOwner")
OrgLevelSponsor = create_org_level_class("OrganizationSponsor")
OrgLevelCopyright = create_org_level_class("OrganizationCopyrightHolder")
OrgLevelAffiliation = create_org_level_class("OrganizationAffiliation")


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
