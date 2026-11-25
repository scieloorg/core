from django import forms
from django.utils.translation import gettext_lazy as _

from collection.models import Collection
from core.forms import CoreAdminModelForm


class IssueAdminModelForm(CoreAdminModelForm):
    collections = forms.ModelMultipleChoiceField(
        label=_("Collections"),
        queryset=Collection.objects.all(),
        required=True,
        widget=forms.CheckboxSelectMultiple,
        help_text=_(
            "Collections in which the issue will be registered (PID). "
            "If none is selected, the journal collections are suggested for confirmation."
        ),
        error_messages={
            "required": _(
                "Confirm at least one collection in which the issue will be registered."
            ),
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # somente na criação do fascículo
            del self.fields["collections"]

    def clean(self):
        cleaned_data = super().clean()
        if "collections" not in self.fields:
            return cleaned_data

        journal = cleaned_data.get("journal")
        if not journal:
            return cleaned_data

        journal_collections = Collection.objects.filter(
            scielojournal__journal=journal
        ).distinct()
        selected = cleaned_data.get("collections")
        if not selected:
            # campo obrigatório (erro já registrado):
            # sugere as coleções do periódico para o usuário confirmar
            self.data = self.data.copy()
            self.data.setlist(
                self.add_prefix("collections"),
                [str(pk) for pk in journal_collections.values_list("pk", flat=True)],
            )
            return cleaned_data

        not_in_journal = selected.exclude(pk__in=journal_collections)
        if not_in_journal.exists():
            self.add_error(
                "collections",
                _("The journal is not registered in: {}").format(
                    ", ".join(str(c) for c in not_in_journal)
                ),
            )
        return cleaned_data
