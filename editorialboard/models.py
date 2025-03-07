import logging
import os
from itertools import cycle
from django.db import models, IntegrityError
from django.db.models import Q, Case, When, Value, IntegerField
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.choices import MONTHS
from core.models import CommonControlField, Gender
from core.forms import CoreAdminModelForm
from core.utils.standardizer import remove_extra_spaces
from journal.models import Journal
from location.models import Location, City, State, Country
from researcher.models import Researcher, Affiliation

from . import choices


class EditorialBoard(CommonControlField, ClusterableModel):
    journal = models.ForeignKey(
        Journal, null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    initial_year = models.CharField(max_length=4, blank=True, null=True)
    final_year = models.CharField(max_length=4, blank=True, null=True)

    autocomplete_search_field = "journal__title"

    def autocomplete_label(self):
        return str(self)

    class Meta:
        unique_together = [("journal", "initial_year", "final_year")]

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
        AutocompletePanel("journal"),
        FieldPanel("initial_year"),
        FieldPanel("final_year"),
        InlinePanel("editorial_board_member", label=_("Member")),
    ]
    base_form_class = CoreAdminModelForm

    def __str__(self):
        return f"{self.journal} {self.initial_year}-{self.final_year}"
    
    
    @property
    def order_by_role(self):
        role_order = [role[0] for role in choices.ROLE]
        order = [When(role__std_role=role, then=Value(i)) for i, role in enumerate(role_order)]

        editorial_members = EditorialBoardMember.objects.filter(editorial_board=self)

        ordered_editorial_board = editorial_members.annotate(
            editorial_order=Case(*order, default=Value(len(role_order)), output_field=IntegerField())
        ).order_by("editorial_order")

        return ordered_editorial_board
    

    @classmethod
    def create_or_update(
        cls,
        user,
        journal,
        initial_year,
        final_year,
        journal_title=None,
    ):
        if not journal and journal_title:
            journal_title = journal_title.strip()
            journal = Journal.objects.get(
                Q(title__icontains=journal_title)
                | Q(official__title__icontains=journal_title)
            )
            logging.info(f"EditorialBoard {journal_title} OK")
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


class EditorialBoardMember(CommonControlField, ClusterableModel, Orderable):
    journal = ParentalKey(
        Journal, related_name="editorial_board_member_journal", null=True
    )
    researcher = models.ForeignKey(
        Researcher, null=True, blank=True, related_name="+", on_delete=models.SET_NULL
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

    panels = [
        AutocompletePanel("researcher"),
        FieldPanel("image"),
        InlinePanel("role_editorial_board", label=_("Role")),
    ]

    base_form_class = CoreAdminModelForm

    def __str__(self):
        return f"{self.researcher.person_name} ({self.role})"

    @staticmethod
    def autocomplete_custom_queryset_filter(any_value):
        return EditorialBoardMember.objects.filter(
            Q(researcher__person_name__fullname__icontains=any_value)
            | Q(researcher__person_name__declared_name__icontains=any_value)
        )

    def autocomplete_label(self):
        return str(self)

    @classmethod
    def _get(
        cls,
        editorial_board,
        researcher,
        role,
    ):
        params = dict(
            editorial_board=editorial_board,
            researcher=researcher,
            role_editorial_board__role=role,
        )
        logging.info(params)
        if role and researcher:
            try:
                return cls.objects.get(**params)
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(*params).first()
        raise ValueError("EditorialBoardMember._get requires editorial_board and researcher and role")

    @classmethod
    def _create(
        cls,
        user,
        researcher,
        editorial_board,
        role,
    ):
        if role and researcher and editorial_board:
            try:
                obj = cls()
                obj.creator = user
                obj.editorial_board = editorial_board
                obj.researcher = researcher
                obj.role = role
                obj.save()
                return obj
            except IntegrityError:
                return cls._get(editorial_board, researcher, role)
        raise ValueError("EditorialBoardMember._create requires editorial_board and researcher and role")

    @classmethod
    def _create_or_update(
        cls,
        user,
        editorial_board,
        researcher,
        role,
    ):
        if role and researcher and editorial_board:
            try:
                return cls._get(editorial_board, researcher, role)
            except cls.DoesNotExist:
                return cls._create(user, editorial_board, researcher, role)
        raise ValueError("EditorialBoardMember._create requires editorial_board and researcher and journal")

    @classmethod
    def create_or_update(
        cls,
        user,
        researcher=None,
        journal=None,
        journal_title=None,
        given_names=None,
        last_name=None,
        suffix=None,
        declared_person_name=None,
        lattes=None,
        orcid=None,
        email=None,
        gender_code=None,
        gender_identification_status=None,
        institution_name=None,
        institution_div1=None,
        institution_div2=None,
        institution_city_name=None,
        institution_country_text=None,
        institution_country_acronym=None,
        institution_country_name=None,
        institution_state_text=None,
        institution_state_acronym=None,
        institution_state_name=None,
        declared_role=None,
        std_role=None,
        member_activity_initial_year=None,
        member_activity_final_year=None,
        member_activity_initial_month=None,
        member_activity_final_month=None,
        editorial_board_initial_year=None,
        editorial_board_final_year=None,
    ):
        if not researcher:
            researcher = Researcher.create_or_update(
                user=user,
                given_names=given_names,
                last_name=last_name,
                declared_name=declared_person_name,
                suffix=suffix,
                lattes=lattes,
                orcid=orcid,
                email=email,
                aff_name=institution_name,
                aff_div1=institution_div1,
                aff_div2=institution_div2,
                aff_city_name=institution_city_name,
                aff_country_text=institution_country_text,
                aff_country_acronym=institution_country_acronym,
                aff_country_name=institution_country_name,
                aff_state_text=institution_state_text,
                aff_state_acronym=institution_state_acronym,
                aff_state_name=institution_state_name,
                gender=gender_code,
                gender_identification_status=gender_identification_status,
            )
        if not journal:
            journal = EditorialBoardMember._get_journal(journal_title=journal_title)

        editorial_board = EditorialBoard.create_or_update(
            user,
            journal,
            editorial_board_initial_year,
            editorial_board_final_year,
        )

        role = None
        if std_role or declared_role:
            role = RoleModel.create_or_update(
                user, std_role=std_role, declared_role=declared_role
            )

        return cls._create_or_update(user, editorial_board, researcher, role)

    @classmethod
    def _get_journal(cls, journal_title):
        try:
            journal_title = journal_title and journal_title.strip()
            return cls.objects.get(
                Q(title__icontains=journal_title)
                | Q(official__title__icontains=journal_title)
            )
        except Journal.DoesNotExist as e:
            logging.info(f"EditorialBoard {journal_title} {e}")


class RoleEditorialBoard(CommonControlField, Orderable):
    editorial_board = ParentalKey(
        EditorialBoardMember, related_name="role_editorial_board"
    )
    role = models.ForeignKey(
        "RoleModel", null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    initial_year = models.CharField(max_length=4, blank=True, null=True)
    final_year = models.CharField(max_length=4, blank=True, null=True)

    panels = [
        AutocompletePanel("role"),
        FieldPanel("initial_year"),
        FieldPanel("final_year"),
    ]

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
