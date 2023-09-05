from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.models import CommonControlField, Gender
from institution.models import Institution, InstitutionHistory
from journal.models import Journal

from . import choices
from .forms import ResearcherForm


class Researcher(ClusterableModel, CommonControlField):
    """
    Class that represent the Researcher
    """

    given_names = models.CharField(
        _("Given names"), max_length=128, blank=True, null=True
    )
    last_name = models.CharField(_("Last name"), max_length=128, blank=True, null=True)
    declared_name = models.CharField(
        _("Declared Name"), max_length=255, blank=True, null=True
    )
    suffix = models.CharField(_("Suffix"), max_length=128, blank=True, null=True)
    orcid = models.TextField(_("ORCID"), blank=True, null=True)
    lattes = models.TextField(_("Lattes"), blank=True, null=True)
    gender = models.ForeignKey(Gender, blank=True, null=True, on_delete=models.SET_NULL)
    gender_identification_status = models.CharField(
        _("Gender identification status"),
        max_length=255,
        choices=choices.GENDER_IDENTIFICATION_STATUS,
        null=True,
        blank=True,
    )

    def autocomplete_label(self):
        return str(self)

    autocomplete_search_field = "given_names"

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "given_names",
                ]
            ),
            models.Index(
                fields=[
                    "last_name",
                ]
            ),
            models.Index(
                fields=[
                    "orcid",
                ]
            ),
            models.Index(
                fields=[
                    "lattes",
                ]
            ),
        ]

    @property
    def get_full_name(self):
        return f"{self.last_name}, {self.given_names}"

    def __unicode__(self):
        return "%s%s, %s (%s)" % (
            self.last_name,
            self.suffix and f" {self.suffix}" or "",
            self.given_names,
            self.orcid,
        )

    def __str__(self):
        return "%s%s, %s (%s)" % (
            self.last_name,
            self.suffix and f" {self.suffix}" or "",
            self.given_names,
            self.orcid,
        )

    @classmethod
    def get_or_create(
        cls,
        given_names,
        last_name,
        declared_name,
        suffix,
        orcid,
        lattes,
        email,
        institution_name,
        gender=None,
        gender_identification_status=None,
        user=None,
    ):
        try:
            return cls.objects.get(
                given_names=given_names,
                last_name=last_name,
                suffix=suffix,
                orcid=orcid,
                lattes=lattes,
                gender=gender,
                gender_identification_status=gender_identification_status,
            )
        except cls.DoesNotExist:
            institution = None
            if institution_name:
                try:
                    institution = Institution.objects.get(name=institution_name)
                except Institution.DoesNotExist:
                    pass
            researcher = cls()
            researcher.given_names = given_names
            researcher.last_name = last_name
            researcher.declared_name = declared_name
            researcher.suffix = suffix
            researcher.orcid = orcid
            researcher.lattes = lattes
            ## TODO
            ## Criar get_or_create para model gender e GenderIdentificationStatus
            researcher.gender = gender
            researcher.gender_identification_status = gender_identification_status
            researcher.creator = user
            researcher.save()
            if email:
                FieldEmail.objects.create(page=researcher, email=email)
            if institution:
                FieldAffiliation.objects.create(
                    page=researcher, institution=institution
                )
            return researcher

    panels = [
        FieldPanel("given_names"),
        FieldPanel("last_name"),
        FieldPanel("suffix"),
        FieldPanel("orcid"),
        FieldPanel("lattes"),
        InlinePanel("page_email", label=_("Email")),
        FieldPanel("gender"),
        FieldPanel("gender_identification_status"),
        InlinePanel("affiliation", label=_("Affiliation")),
    ]

    base_form_class = ResearcherForm


class FieldEmail(Orderable):
    page = ParentalKey(Researcher, on_delete=models.CASCADE, related_name="page_email")
    email = models.EmailField(_("Email"), max_length=128, blank=True, null=True)


class FieldAffiliation(Orderable, InstitutionHistory):
    page = ParentalKey(Researcher, on_delete=models.CASCADE, related_name="affiliation")


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
    initial_year = models.IntegerField(blank=True, null=True)
    initial_month = models.IntegerField(blank=True, null=True, choices=choices.MONTHS)
    final_year = models.IntegerField(blank=True, null=True)
    final_month = models.IntegerField(blank=True, null=True, choices=choices.MONTHS)

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
