from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.edit_handlers import FieldPanel, InlinePanel
from wagtail.core.models import Orderable

from core.models import CommonControlField, Gender, GenderIdentificationStatus
from institution.models import Institution, InstitutionHistory

from .forms import ResearcherForm


class Researcher(ClusterableModel, CommonControlField):
    """
    Class that represent the Researcher
    """
    given_names = models.CharField(
        _("Given names"), max_length=128, blank=False, null=False
    )
    last_name = models.CharField(
        _("Last name"), max_length=128, blank=False, null=False
    )
    suffix = models.CharField(_("Suffix"), max_length=128, blank=True, null=True)
    orcid = models.TextField(_("ORCID"), blank=True, null=True)
    lattes = models.TextField(_("Lattes"), blank=True, null=True)
    gender = models.ForeignKey(Gender, blank=True, null=True, on_delete=models.SET_NULL)
    gender_identification_status = models.ForeignKey(
        GenderIdentificationStatus, blank=True, null=True, on_delete=models.SET_NULL)

    def autocomplete_label(self):
        return str(self)

    autocomplete_search_field = 'given_names'

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
