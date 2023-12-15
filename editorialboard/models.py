import logging
import os

from django.db import models, IntegrityError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey, ParentalManyToManyField
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
from editorialboard.forms import EditorialboardForm, EditorialboardRoleForm


class EditorialBoard(CommonControlField, ClusterableModel):
    journal = models.ForeignKey(
        Journal, null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    initial_year = models.CharField(max_length=4, blank=True, null=True)
    final_year = models.CharField(max_length=4, blank=True, null=True)

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
        InlinePanel("editorial_board_role", label=_("Editorial Board Role"), classname="collapsed",),
    ]
    base_form_class = EditorialboardForm

    def __str__(self):
        return f"{self.journal.title} {self.initial_year}-{self.final_year}"

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


class EditorialBoardRole(Orderable, CommonControlField):
    editorial_board = ParentalKey(
        EditorialBoard,
        on_delete=models.SET_NULL,
        related_name="editorial_board_role",
        null=True,
    )
    role = models.ForeignKey(
        "RoleModel", null=True, blank=True, on_delete=models.SET_NULL
    )

    # FIXME https://github.com/wagtail/django-modelcluster
    # https://github.com/wagtail/wagtail/issues/5432
    members = ParentalManyToManyField(
        "EditorialBoardMember",
        blank=True,
    )

    class Meta:
        unique_together = [
            (
                "editorial_board",
                "role",
            )
        ]
        indexes = [
            models.Index(
                fields=[
                    "editorial_board",
                ]
            ),
            models.Index(
                fields=[
                    "role",
                ]
            ),
        ]

    panels = [
        # AutocompletePanel("editorial_board"),
        AutocompletePanel("role"),
        AutocompletePanel("members"),
    ]
    base_form_class = EditorialboardRoleForm

    @classmethod
    def _get(
        cls,
        editorial_board,
        role,
    ):
        if editorial_board and role:
            try:
                return cls.objects.get(
                    editorial_board=editorial_board,
                    role=role,
                )
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(
                    editorial_board=editorial_board,
                    role=role,
                ).first()
        raise ValueError("EditorialBoardRole.get requires editorial_board and role")

    @classmethod
    def _create(
        cls,
        user,
        editorial_board,
        role,
    ):
        try:
            obj = cls()
            obj.creator = user
            obj.editorial_board = editorial_board
            obj.role = role
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(
                editorial_board,
                role,
            )

    @classmethod
    def create_or_update(
        cls,
        user,
        editorial_board,
        role,
        declared_role=None,
        std_role=None,
    ):
        if not role and (std_role or declared_role):
            role = RoleModel.create_or_update(
                user, std_role=std_role, declared_role=declared_role
            )
        if role and editorial_board:
            try:
                return cls._get(editorial_board, role)
            except cls.DoesNotExist:
                return cls._create(user, editorial_board, role)
        raise ValueError(
            "EditorialBoardRole.create_or_update requires editorial_board and role"
        )


class EditorialBoardMember(CommonControlField, ClusterableModel):
    journal = models.ForeignKey(
        Journal, null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )
    researcher = models.ForeignKey(
        Researcher, null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )

    class Meta:
        unique_together = [("researcher", "journal")]

    panels = [
        AutocompletePanel("researcher"),
        AutocompletePanel("journal"),
        InlinePanel("editorial_board_member_activity", label=_("Editorial Board Menber Activity")),
    ]
    base_form_class = CoreAdminModelForm

    def __str__(self):
        return f"{self.researcher} | {self.journal}"

    @staticmethod
    def autocomplete_custom_queryset_filter(any_value):
        return EditorialBoardMember.objects.filter(
            Q(researcher__person_name__fullname__icontains=any_value)
            | Q(researcher__person_name__declared_name__icontains=any_value)
        )

    def autocomplete_label(self):
        return f"{self.researcher} | {self.journal.title}"

    @classmethod
    def _get(
        cls,
        researcher,
        journal,
    ):
        logging.info(
            dict(
                researcher=researcher,
                journal=journal,
            )
        )
        if journal and researcher:
            try:
                return cls.objects.get(
                    researcher=researcher,
                    journal=journal,
                )
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(
                    researcher=researcher,
                    journal=journal,
                ).first()
        raise ValueError("EditorialBoardMember._get requires researcher and journal")

    @classmethod
    def _create(
        cls,
        user,
        researcher,
        journal,
    ):
        if journal and researcher:
            try:
                obj = cls()
                obj.creator = user
                obj.researcher = researcher
                obj.journal = journal
                obj.save()
                return obj
            except IntegrityError:
                return cls._get(researcher, journal)
        raise ValueError("EditorialBoardMember._create requires researcher and journal")

    @classmethod
    def _create_or_update(
        cls,
        user,
        researcher,
        journal,
    ):
        if journal and researcher:
            try:
                return cls._get(researcher, journal)
            except cls.DoesNotExist:
                return cls._create(user, researcher, journal)
        raise ValueError("EditorialBoardMember._create requires researcher and journal")

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
            researcher = EditorialBoardMember._create_or_update_researcher(
                user,
                given_names,
                last_name,
                suffix,
                declared_person_name,
                lattes,
                orcid,
                email,
                gender_code,
                gender_identification_status,
                institution_name,
                institution_div1,
                institution_div2,
                institution_city_name,
                institution_country_text,
                institution_country_acronym,
                institution_country_name,
                institution_state_text,
                institution_state_acronym,
                institution_state_name,
            )
        if not journal:
            journal = EditorialBoardMember._create_or_update_journal(journal_title)

        member = cls._create_or_update(user, researcher, journal)

        role = None
        if std_role or declared_role:
            role = RoleModel.create_or_update(
                user, std_role=std_role, declared_role=declared_role
            )

        member.add_member_activity(
            user,
            role,
            member_activity_initial_year=member_activity_initial_year,
            member_activity_initial_month=member_activity_initial_month,
            member_activity_final_year=member_activity_final_year,
            member_activity_final_month=member_activity_final_month,
        )

        member.add_member_to_editorial_board(
            user,
            role,
            editorial_board_initial_year,
            editorial_board_final_year,
        )
        return member

    @staticmethod
    def _create_or_update_researcher(
        user,
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
    ):
        location = EditorialBoardMember._create_or_update_location(
            user,
            institution_city_name,
            institution_country_text,
            institution_country_acronym,
            institution_country_name,
            institution_state_text,
            institution_state_acronym,
            institution_state_name,
        )
        affiliation = Affiliation.create_or_update(
            user,
            name=institution_name,
            acronym=None,
            level_1=institution_div1,
            level_2=institution_div2,
            level_3=None,
            location=location,
            official=None,
            is_official=None,
            url=None,
            institution_type=None,
        )
        gender = Gender.create_or_update(user, code=gender_code, gender=gender_code)
        return Researcher.create_or_update(
            user,
            given_names=given_names,
            last_name=last_name,
            suffix=suffix,
            declared_name=declared_person_name,
            affiliation=affiliation,
            year=None,
            orcid=orcid,
            lattes=lattes,
            other_ids=None,
            email=email,
            gender=gender,
            gender_identification_status=gender_identification_status,
        )

    @staticmethod
    def _create_or_update_location(
        user,
        city_name=None,
        country_text=None,
        country_acronym=None,
        country_name=None,
        state_text=None,
        state_acronym=None,
        state_name=None,
    ):
        state = None
        country = None
        if state_text:
            for item in State.standardize(state_text, user):
                state = item.get("state")
        if country_text:
            for item in Country.standardize(country_text, user):
                country = item.get("country")

        try:
            return Location.create_or_update(
                user,
                country=country,
                country_name=country_name,
                country_acron3=None,
                country_acronym=country_acronym,
                state=state,
                state_name=state_name,
                state_acronym=state_acronym,
                city=None,
                city_name=city_name,
                lang=None,
            )
        except Exception as e:
            logging.exception(e)
            return

    @staticmethod
    def _create_or_update_journal(journal_title):
        try:
            journal_title = journal_title and journal_title.strip()
            return Journal.objects.get(
                Q(title__icontains=journal_title)
                | Q(official__title__icontains=journal_title)
            )
            logging.info(f"EditorialBoard {journal_title} OK")
        except Journal.DoesNotExist as e:
            logging.info(f"EditorialBoard {journal_title} {e}")

    def add_member_to_editorial_board(
        self,
        user,
        role,
        editorial_board_initial_year=None,
        editorial_board_final_year=None,
    ):
        editorial_board = EditorialBoard.create_or_update(
            user,
            self.journal,
            editorial_board_initial_year,
            editorial_board_final_year,
        )
        editorial_board_role = EditorialBoardRole.create_or_update(
            user,
            editorial_board,
            role,
        )
        editorial_board_role.members.add(self)
        editorial_board_role.save()

    def add_member_activity(
        self,
        user,
        role,
        member_activity_initial_year=None,
        member_activity_initial_month=None,
        member_activity_final_year=None,
        member_activity_final_month=None,
    ):
        EditorialBoardMemberActivity.create_or_update(
            user,
            self,
            role=role,
            initial_year=member_activity_initial_year,
            initial_month=member_activity_initial_month,
            final_year=member_activity_final_year,
            final_month=member_activity_final_month,
        )


class EditorialBoardMemberActivity(CommonControlField, Orderable):
    member = ParentalKey(
        EditorialBoardMember,
        null=True,
        blank=True,
        related_name="editorial_board_member_activity",
        on_delete=models.SET_NULL,
    )
    role = models.ForeignKey(
        "RoleModel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    initial_year = models.CharField(max_length=4, blank=True, null=True)
    initial_month = models.CharField(
        max_length=2, blank=True, null=True, choices=MONTHS
    )
    final_year = models.CharField(max_length=4, blank=True, null=True)
    final_month = models.CharField(max_length=2, blank=True, null=True, choices=MONTHS)

    base_form_class = CoreAdminModelForm

    panels = [
        FieldPanel("member"),
        AutocompletePanel("role"),
        FieldPanel("initial_year"),
        FieldPanel("initial_month"),
        FieldPanel("final_year"),
        FieldPanel("final_month"),
    ]

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "initial_year",
                ]
            ),
            models.Index(
                fields=[
                    "initial_month",
                ]
            ),
            models.Index(
                fields=[
                    "role",
                ]
            ),
        ]

    @classmethod
    def _get(
        cls,
        member,
        role,
        initial_year,
        initial_month,
    ):
        if member and initial_year and role and initial_month:
            try:
                return cls.objects.get(
                    member=member,
                    initial_year=initial_year,
                    role=role,
                    initial_month=initial_month,
                )
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(
                    member=member,
                    initial_year=initial_year,
                    role=role,
                    initial_month=initial_month,
                ).first()
        raise ValueError(
            "EditorialBoardMember._get requires member and initial_year and initial_month and role"
        )

    @classmethod
    def _create(
        cls,
        user,
        member,
        role,
        initial_year,
        initial_month,
        final_year,
        final_month,
    ):
        if member and initial_year and role and initial_month:
            try:
                obj = cls()
                obj.creator = user
                obj.member = member
                obj.role = role
                obj.initial_year = initial_year
                obj.initial_month = initial_month or obj.initial_month
                obj.final_year = final_year
                obj.final_month = final_month or obj.final_month
                obj.save()
                return obj
            except IntegrityError:
                return cls.get(
                    member,
                    role,
                    initial_year,
                    initial_month,
                )
        raise ValueError(
            "EditorialBoardMember._create requires member and initial_year and initial_month and role"
        )

    @classmethod
    def create_or_update(
        cls,
        user,
        member,
        role,
        initial_year,
        initial_month,
        final_year,
        final_month,
    ):
        if member and initial_year and role and initial_month:
            try:
                return cls._get(member, role, initial_year, initial_month)
            except cls.DoesNotExist:
                return cls._create(
                    user,
                    member,
                    role,
                    initial_year,
                    initial_month,
                    final_year,
                    final_month,
                )
        raise ValueError(
            "EditorialBoardMember.create_or_update requires member and initial_year and initial_month and role"
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
