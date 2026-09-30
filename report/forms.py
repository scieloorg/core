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
    )
    thematic_area = forms.ModelChoiceField(
        queryset=ThematicArea.objects.all(),
        required=False,
        label=_("Thematic Area"),
    )
    journal = forms.ModelChoiceField(
        queryset=Journal.objects.order_by("title"),
        required=False,
        label=_("Journal"),
    )
    pid = forms.CharField(
        required=False,
        label=_("PID v2 or v3"),
        max_length=23,
    )
