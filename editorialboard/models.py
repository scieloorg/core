import os

from django.db import models
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
