from django import forms
from django.utils.translation import gettext_lazy as _

from collection.models import Collection
from journal.models import Journal
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
