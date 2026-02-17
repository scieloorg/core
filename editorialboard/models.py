import logging
import os

from django.db import IntegrityError, models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField
from core.utils.standardizer import remove_extra_spaces
from journal.models import Journal
from researcher.models import NewResearcher

from . import choices


class EditorialBoardMember(CommonControlField, ClusterableModel, Orderable):
    journal = ParentalKey(
        Journal, related_name="editorial_board_member_journal", null=True
    )
    researcher = models.ForeignKey(
        NewResearcher, null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    image = models.ForeignKey(
        "wagtailimages.Image", 
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=_("Upload a profile photo of the editorial board member."),
    )
    area = models.TextField(null=True, blank=True)
    
    class Meta:
        unique_together = [("journal", "researcher")]
        indexes = [
            models.Index(
                fields=[
                    "researcher",
                ]
            ),
        ]

    panels = [
        AutocompletePanel("researcher"),
        FieldPanel("image"),
        InlinePanel("role_editorial_board", label=_("Role")),
    ]

    base_form_class = CoreAdminModelForm

    def __str__(self):
        if not self.researcher:
            return "None"
        return f"{self.researcher.fullname} {', '.join(self.role_names)}"

    @property
    def role_names(self):
        return [
            role.role_name
            for role in self.role_editorial_board.filter(role__role__isnull=False)
        ]

    @staticmethod
    def autocomplete_custom_queryset_filter(search_term):
        return EditorialBoardMember.objects.filter(researcher__fullname__icontains=search_term).prefetch_related("researcher")
    
    def autocomplete_label(self):
        return str(self)

    @classmethod
    def _get(
        cls,
        journal,
        researcher,
    ):
        params = dict(
            journal=journal,
            researcher=researcher,
        )
        if researcher and journal:
                return cls.objects.get(**params)
        raise ValueError("EditorialBoardMember._get requires journal and researcher and role")

    @classmethod
    def _create(
        cls,
        user,
        journal,
        researcher,
    ):
        if researcher and journal:
            try:
                obj = cls()
                obj.creator = user
                obj.journal = journal
                obj.researcher = researcher
                obj.save()
                return obj
            except IntegrityError:
                return cls._get(journal, researcher)
        raise ValueError("EditorialBoardMember._create requires journal and researcher and role")

    @classmethod
    def _create_or_update(
        cls,
        user,
        journal,
        researcher, 
    ):
        if researcher and journal:
            try:
                return cls._get(journal, researcher)
            except cls.DoesNotExist:
                return cls._create(user, journal, researcher)
        raise ValueError("EditorialBoardMember._create requires journal and researcher and journal")

    @classmethod
    def create_or_update(
        cls,
        user,
        researcher=None,
        journal=None,
        declared_role=None,
        std_role=None,
        editorial_board_initial_year=None,
        editorial_board_final_year=None,
    ):
        
        role = None
        if std_role or declared_role:
            role = RoleModel.create_or_update(
                user, std_role=std_role, declared_role=declared_role
            )
        editorial_board_member = EditorialBoardMember._create_or_update(
            user,
            journal,
            researcher,
        )

        role_editorial_board = RoleEditorialBoard.create_or_update(
            editorial_board_member,
            role,
            editorial_board_initial_year,
            editorial_board_final_year,
        )
        return editorial_board_member

    @staticmethod
    def _get_journal(journal_title):
        try:
            journal_title = journal_title and journal_title.strip()
            return Journal.objects.get(
                Q(title__icontains=journal_title)
                | Q(official__title__icontains=journal_title)
            )
        except Journal.DoesNotExist as e:
            logging.info(f"EditorialBoard {journal_title} {e}")

    @classmethod
    def get_editorial_board_with_role(cls, journal):
        editorial_board_by_latest_role = {}
        editorial_board_members = cls.objects.filter(journal=journal) \
            .prefetch_related(
                "role_editorial_board",
                "researcher__orcid",
                "researcher__affiliation__location"
            )
        for member in editorial_board_members:
            member_role = member.role_editorial_board.filter(
                role__role__std_role__isnull=False
            ).order_by("-initial_year").first()
            researcher = member.researcher
            editorial_board_by_latest_role[member_role.role_name].append(researcher.data)
        return editorial_board_by_latest_role


class RoleEditorialBoard(CommonControlField, Orderable):
    editorial_board = ParentalKey(
        EditorialBoardMember, related_name="role_editorial_board"
    )
    role = models.ForeignKey(
        "RoleModel", null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    initial_year = models.DateField(blank=True, null=True)
    final_year = models.DateField(blank=True, null=True)

    panels = [
        AutocompletePanel("role"),
        FieldPanel("initial_year"),
        FieldPanel("final_year"),
    ]

    def __str__(self):
        return f"{self.role}"

    @property
    def role_name(self):
        try:
            return self.role.std_role or self.role.declared_role
        except AttributeError:
            return None

    @classmethod
    def get(
        cls,
        editorial_board_member,
        role,
        initial_year,
        final_year,
        ):
        params = dict(
            editorial_board=editorial_board_member,
            role=role,
            initial_year=initial_year,
            final_year=final_year,
        )
        if editorial_board_member and role:
            return cls.objects.get(**params)
        raise ValueError("RoleEditorialBoard.get requires editorial_board_member and role")
    
    @classmethod
    def create(
        cls,
        editorial_board_member,
        role,
        initial_year,
        final_year,
        ):
        obj = cls()
        obj.editorial_board = editorial_board_member
        obj.role = role
        obj.initial_year = initial_year
        obj.final_year = final_year
        obj.save()
        return obj

    @classmethod
    def create_or_update(
        cls,
        editorial_board_member,
        role,
        initial_year,
        final_year,
        ):
        try:
            return cls.get(editorial_board_member, role, initial_year, final_year)
        except cls.DoesNotExist:
            return cls.create(editorial_board_member, role, initial_year, final_year)


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

    base_form_class = CoreAdminModelForm

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
    def create_or_update(
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
    def _get(
        cls,
        declared_role,
        std_role,
    ):
        if declared_role or std_role:
            try:
                return cls.objects.get(declared_role=declared_role, std_role=std_role)
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(
                    declared_role=declared_role, std_role=std_role
                ).first()
        raise ValueError("RoleModel.get requires declared_role or std_role")

    @classmethod
    def _create(
        cls,
        user,
        declared_role,
        std_role,
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

        raise ValueError("RoleModel.create requires declared_role or std_role")

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
            or "section" in declared_role
        ):
            return choices.ASSOCIATE_EDITOR

    @classmethod
    def load(cls, user):
        for item in choices.ROLE:
            std_role, declared_role = item
            cls.create_or_update(
                user,
                declared_role=declared_role,
                std_role=std_role,
            )
