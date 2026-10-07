from django import forms
from django.utils.translation import gettext_lazy as _

from collection.models import Collection
from journal.models import Journal
from report.data_availability import GROUP_BY_ISSUE_YEAR, GROUP_BY_OPTIONS
from thematic_areas.models import ThematicArea


class VisualElementTotalsFilterForm(forms.Form):
    collection = forms.ModelChoiceField(
        queryset=Collection.objects.all(),
        required=False,
        label=_("Collection"),
        empty_label="",
    )
    thematic_area = forms.ModelChoiceField(
        queryset=ThematicArea.objects.all(),
        required=False,
        label=_("Thematic Area"),
        empty_label="",
    )
    journal = forms.ModelChoiceField(
        queryset=Journal.objects.order_by("title"),
        required=False,
        label=_("Journal"),
        empty_label="",
    )
    pid = forms.CharField(
        required=False,
        label=_("PID v2 or v3"),
        max_length=23,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["journal"].queryset = Journal.objects.order_by("title").prefetch_related(
            "scielojournal_set"
        )


class DataAvailabilityFilterForm(forms.Form):
    collection = forms.ModelChoiceField(
        queryset=Collection.objects.order_by("acron3"),
        required=False,
        label=_("Collection"),
        empty_label=_("All"),
    )
    journal = forms.ModelChoiceField(
        queryset=Journal.objects.order_by("title"),
        required=False,
        label=_("Journal"),
        empty_label=_("All"),
    )
    year_from = forms.RegexField(
        regex=r"^\d{4}$",
        required=False,
        label=_("Online publication from"),
    )
    year_to = forms.RegexField(
        regex=r"^\d{4}$",
        required=False,
        label=_("Online publication to"),
    )
    group_by = forms.ChoiceField(
        choices=GROUP_BY_OPTIONS,
        required=False,
        label=_("Group by"),
    )

    def filters(self):
        """
        Filtros válidos; campos inválidos são ignorados em vez de
        invalidar o relatório inteiro.
        """
        self.is_valid()
        data = getattr(self, "cleaned_data", {})
        return {
            "collection": data.get("collection"),
            "journal": data.get("journal"),
            "year_from": data.get("year_from") or None,
            "year_to": data.get("year_to") or None,
            "group_by": data.get("group_by") or GROUP_BY_ISSUE_YEAR,
        }
