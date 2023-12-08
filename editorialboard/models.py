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
from journal.models import Journal
from researcher.models import Researcher

from . import choices


class EditorialBoard(CommonControlField, ClusterableModel):
    journal = models.ForeignKey(
        Journal, null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    initial_year = models.CharField(max_length=4, blank=True, null=True)
    final_year = models.CharField(max_length=4, blank=True, null=True)

    class Meta:
        unique_together = [["journal", "initial_year", "final_year"]]

        indexes = [
            models.Index(
                fields=[
                    "initial_year",
                ]
            ),
            models.Index(
                fields=[
                    "final_year",
                ]
            ),
        ]

    panels = [
        FieldPanel("initial_year"),
        FieldPanel("final_year"),
        # InlinePanel("editorial_board_member"),
    ]
    base_form_class = CoreAdminModelForm

    def __str__(self):
        return f"{self.journal.title} {self.initial_year}-{self.final_year}"

    @classmethod
    def get_or_create(
        cls,
        journal,
        initial_year,
        final_year,
        user=None,
    ):
        try:
            return cls.get(journal, initial_year, final_year)
        except cls.DoesNotExist:
            return cls.create(user, journal, initial_year, final_year)

    @classmethod
    def get(
        cls,
        journal,
        initial_year,
        final_year,
    ):
        try:
            return cls.objects.get(
                journal=journal,
                initial_year=initial_year,
                final_year=final_year,
            )
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(
                journal=journal,
                initial_year=initial_year,
                final_year=final_year,
            ).first()

    @classmethod
    def create(
        cls,
        user,
        journal,
        initial_year,
        final_year,
    ):
        try:
            obj = cls()
            obj.creator = user
            obj.journal = journal
            obj.initial_year = initial_year
            obj.final_year = final_year
            obj.save()
            return obj
        except IntegrityError:
            return cls.objects.get(
                journal=journal,
                initial_year=initial_year,
                final_year=final_year,
            )


class EditorialBoardMember(models.Model):
    journal = models.ForeignKey(
        Journal, null=True, blank=True, related_name="+", on_delete=models.CASCADE
    )
    member = models.ForeignKey(
        Researcher, null=True, blank=True, related_name="+", on_delete=models.CASCADE
    )
    role = models.CharField(
        _("Role"), max_length=255, choices=choices.ROLE, null=False, blank=False
    )
    initial_year = models.CharField(max_length=4, blank=True, null=True)
    initial_month = models.CharField(
        max_length=2, blank=True, null=True, choices=MONTHS
    )
    final_year = models.CharField(max_length=4, blank=True, null=True)
    final_month = models.CharField(max_length=2, blank=True, null=True, choices=MONTHS)

    panels = [
        AutocompletePanel("journal"),
        AutocompletePanel("member"),
        FieldPanel("role"),
        FieldPanel("initial_year"),
        FieldPanel("initial_month"),
        FieldPanel("final_year"),
        FieldPanel("final_month"),
    ]

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "journal",
                ]
            ),
            models.Index(
                fields=[
                    "member",
                ]
            ),
            models.Index(
                fields=[
                    "role",
                ]
            ),
        ]

    @classmethod
    def get_or_create(
        self,
        journal,
        role,
        initial_year,
        email,
        institution_name,
        given_names,
        last_name,
        suffix,
        orcid,
        lattes,
        gender,
        gender_identification_status,
        user,
    ):
        try:
            gender = Gender.objects.get(code=gender)
        except Gender.DoesNotExist:
            gender = None

        researcher_get = Researcher.get_or_create(
            given_names,
            last_name,
            suffix,
            orcid,
            lattes,
            email,
            institution_name,
            gender,
            gender_identification_status,
            user,
        )

        try:
            journal_get = Journal.objects.get(title=journal)
            return EditorialBoardMember.objects.get(
                journal=journal_get, member=researcher_get
            )
        except Journal.DoesNotExist as e:
            # TODO fazer tratamento apropriado para periódico não registrado
            raise e
        except EditorialBoardMember.DoesNotExist:
            editorial_board_member = EditorialBoardMember()
            editorial_board_member.member = researcher_get
            editorial_board_member.journal = journal_get
            editorial_board_member.role = role
            editorial_board_member.initial_year = initial_year
            editorial_board_member.creator = user
            editorial_board_member.save()
            return editorial_board_member

    def __str__(self):
        return "%s (%s)" % (
            self.member or "",
            self.role or "",
        )


class EditorialBoardMemberFile(models.Model):
    attachment = models.ForeignKey(
        "wagtaildocs.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    is_valid = models.BooleanField(_("Is valid?"), default=False, blank=True, null=True)
    line_count = models.IntegerField(
        _("Number of lines"), default=0, blank=True, null=True
    )

    def filename(self):
        return os.path.basename(self.attachment.name)

    panels = [FieldPanel("attachment")]


class RoleModel(CommonControlField):
    std_role = models.CharField(
        _("Role"), max_length=16, choices=choices.ROLE, null=True, blank=True
    )
    declared_role = models.CharField(
        _("Declared Role"), max_length=128, null=True, blank=True
    )

    class Meta:
        unique_together = ["declared_role", "std_role"]
        indexes = [
            models.Index(
                fields=[
                    "declared_role",
                ]
            ),
            models.Index(
                fields=[
                    "std_role",
                ]
            ),
        ]

    def __str__(self):
        return f"{self.std_role} | {self.declared_role}"

    @staticmethod
    def autocomplete_custom_queryset_filter(any_value):
        return RoleModel.objects.filter(
            Q(declared_role__icontains=any_value) | Q(std_role__icontains=any_value)
        )

    def autocomplete_label(self):
        return f"{self.std_role} | {self.declared_role}"

    @classmethod
    def get_or_create(
        cls,
        user,
        declared_role,
        std_role,
    ):
        if declared_role or std_role:
            try:
                declared_role = remove_extra_spaces(declared_role)
                std_role = remove_extra_spaces(std_role)
                std_role = std_role or RoleModel.get_std_role(declared_role)
                return cls._get(declared_role, std_role)
            except cls.DoesNotExist:
                return cls._create(user, declared_role, std_role)
        raise ValueError(
            "RoleModel.create_or_update requires declared_role or std_role"
        )

    @classmethod
    def get(
        cls,
        declared_role,
        std_role,
    ):
        if declared_role or std_role:
            try:
                return cls.objects.get(declared_role=declared_role, std_role=std_role)
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(declared_role=declared_role, std_role=std_role).first()
        raise ValueError(
            "RoleModel.get requires declared_role or std_role"
        )

    @classmethod
    def _create(
        cls,
        user,
        declared_role,
        role,
    ):
        if declared_role or std_role:
            try:
                obj = cls()
                obj.creator = user
                obj.declared_role = declared_role
                obj.std_role = std_role
                obj.save()
                return obj
            except IntegrityError as e:
                return cls.objects.get(declared_role=declared_role, std_role=std_role)

        raise ValueError(
            "RoleModel.create requires declared_role or std_role"
        )

    @staticmethod
    def get_std_role(declared_role):
        # EDITOR_IN_CHIEF = "in-chief"
        # EXECUTIVE_EDITOR = "executive"
        # ASSOCIATE_EDITOR = "associate"
        # TECHNICAL_TEAM = "technical"
        if not declared_role:
            return None
        declared_role = declared_role.lower()
        if "chef" in declared_role:
            return choices.EDITOR_IN_CHIEF
        if len(declared_role.split()) == 1 or "exec" in declared_role:
            return choices.EXECUTIVE_EDITOR
        if (
            "assoc" in declared_role
            or "área" in declared_role
            or "seç" in declared_role
            or "cient" in declared_role
            or "editor " in declared_role
        ):
            return choices.ASSOCIATE_EDITOR
