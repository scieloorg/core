from django import forms
from django.utils.translation import gettext_lazy as _

from core.forms import CoreAdminModelForm
from organization.models import Organization
from location.models import Country, Location


class OrganizationMixin:
    """
    Mixin para adicionar campos de entrada manual de organização
    que não estão presentes na lista padrão de Organization.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Adiciona campos para entrada manual de organização
        self.fields["manual_org_name"] = forms.CharField(
            label=_("Organization Name (Manual)"),
            max_length=255,
            required=False,
            help_text=_("Enter organization name if not found in the list above"),
            widget=forms.TextInput(
                attrs={"placeholder": _("Enter standardized organization name")}
            ),
        )

        self.fields["manual_city"] = forms.CharField(
            label=_("City"),
            max_length=100,
            required=False,
            help_text=_("City where organization is located"),
        )

        self.fields["manual_state"] = forms.CharField(
            label=_("State/Province"),
            max_length=100,
            required=False,
            help_text=_("State or province where organization is located"),
        )

        self.fields["manual_country"] = forms.ModelChoiceField(
            label=_("Country"),
            queryset=Country.objects.all(),
            required=False,
            help_text=_("Country where organization is located"),
            empty_label=_("Select country..."),
        )

    def clean(self):
        cleaned_data = super().clean()
        organization = cleaned_data.get("organization")
        manual_org_name = cleaned_data.get("manual_org_name")

        # Validação: deve ter organization OU manual_org_name
        if not organization and not manual_org_name:
            raise forms.ValidationError(
                _(
                    "Please either select an organization from the list or enter manual organization data."
                )
            )

        # Se tem manual_org_name, deve ter pelo menos o país
        if manual_org_name and not cleaned_data.get("manual_country"):
            raise forms.ValidationError(
                _("When entering manual organization data, country is required.")
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Se não tem organization mas tem dados manuais, cria/busca organization
        if not instance.organization and self.cleaned_data.get("manual_org_name"):
            organization = self._create_or_get_organization()
            if organization:
                instance.organization = organization

        if commit:
            instance.save()
        return instance

    def _create_or_get_organization(self):
        """Cria ou busca Organization baseado nos dados manuais."""
        manual_name = self.cleaned_data.get("manual_org_name")
        manual_city = self.cleaned_data.get("manual_city")
        manual_state = self.cleaned_data.get("manual_state")
        manual_country = self.cleaned_data.get("manual_country")

        if not manual_name:
            return None

        # Busca organization existente primeiro
        existing_org = Organization.objects.filter(name=manual_name).first()
        if existing_org:
            return existing_org

        # Cria location se tiver dados geográficos
        location = None
        if manual_country:
            try:
                # Busca ou cria location (simplificado)
                location_data = {"country": manual_country}
                location, created = Location.objects.get_or_create(**location_data)
            except Exception:
                location = None

        # Cria nova organization
        try:
            organization = Organization.objects.create(
                name=manual_name,
                location=location,
                source="user",  # Marca como fonte user
            )
            return organization
        except Exception:
            # Se não conseguir criar, retorna None - usuário terá que usar lista padrão
            return None


class OwnerHistoryForm(OrganizationMixin, CoreAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define o model dinamicamente para evitar importação circular
        if not hasattr(self._meta, "model") or self._meta.model is None:
            from journal.models import OwnerHistory

            self._meta.model = OwnerHistory


class PublisherHistoryForm(OrganizationMixin, CoreAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define o model dinamicamente para evitar importação circular
        if not hasattr(self._meta, "model") or self._meta.model is None:
            from journal.models import PublisherHistory

            self._meta.model = PublisherHistory


class SponsorHistoryForm(OrganizationMixin, CoreAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define o model dinamicamente para evitar importação circular
        if not hasattr(self._meta, "model") or self._meta.model is None:
            from journal.models import SponsorHistory

            self._meta.model = SponsorHistory


class CopyrightHolderHistoryForm(OrganizationMixin, CoreAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define o model dinamicamente para evitar importação circular
        if not hasattr(self._meta, "model") or self._meta.model is None:
            from journal.models import CopyrightHolderHistory

            self._meta.model = CopyrightHolderHistory


class SciELOJournalModelForm(CoreAdminModelForm):
    """
    Mixin para adicionar campos de entrada manual de organização
    que não estão presentes na lista padrão de Organization.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Adiciona campos para entrada manual de organização
        self.fields["manual_org_name"] = forms.CharField(
            label=_("Organization Name (Manual)"),
            max_length=255,
            required=False,
            help_text=_("Enter organization name if not found in the list above"),
            widget=forms.TextInput(
                attrs={"placeholder": _("Enter standardized organization name")}
            ),
        )

        self.fields["manual_city"] = forms.CharField(
            label=_("City"),
            max_length=100,
            required=False,
            help_text=_("City where organization is located"),
        )

        self.fields["manual_state"] = forms.CharField(
            label=_("State/Province"),
            max_length=100,
            required=False,
            help_text=_("State or province where organization is located"),
        )

        self.fields["manual_country"] = forms.ModelChoiceField(
            label=_("Country"),
            queryset=Country.objects.all(),
            required=False,
            help_text=_("Country where organization is located"),
            empty_label=_("Select country..."),
        )

    def clean(self):
        cleaned_data = super().clean()
        organization = cleaned_data.get("organization")
        manual_org_name = cleaned_data.get("manual_org_name")

        # Validação: deve ter organization OU manual_org_name
        if not organization and not manual_org_name:
            raise forms.ValidationError(
                _(
                    "Please either select an organization from the list or enter manual organization data."
                )
            )

        # Se tem manual_org_name, deve ter pelo menos o país
        if manual_org_name and not cleaned_data.get("manual_country"):
            raise forms.ValidationError(
                _("When entering manual organization data, country is required.")
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Se não tem organization mas tem dados manuais, cria/busca organization
        if not instance.organization and self.cleaned_data.get("manual_org_name"):
            organization = self._create_or_get_organization()
            if organization:
                instance.organization = organization

        if commit:
            instance.save()
        return instance

    def _create_or_get_organization(self):
        """Cria ou busca Organization baseado nos dados manuais."""
        manual_name = self.cleaned_data.get("manual_org_name")
        manual_city = self.cleaned_data.get("manual_city")
        manual_state = self.cleaned_data.get("manual_state")
        manual_country = self.cleaned_data.get("manual_country")

        if not manual_name:
            return None

        # Busca organization existente primeiro
        existing_org = Organization.objects.filter(name=manual_name).first()
        if existing_org:
            return existing_org

        # Cria location se tiver dados geográficos
        location = None
        if manual_country:
            try:
                # Busca ou cria location (simplificado)
                location_data = {"country": manual_country}
                location, created = Location.objects.get_or_create(**location_data)
            except Exception:
                location = None

        # Cria nova organization
        try:
            organization = Organization.objects.create(
                name=manual_name,
                location=location,
                source="user",  # Marca como fonte user
            )
            return organization
        except Exception:
            # Se não conseguir criar, retorna None - usuário terá que usar lista padrão
            return None


class OwnerHistoryForm(OrganizationMixin, CoreAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define o model dinamicamente para evitar importação circular
        if not hasattr(self._meta, "model") or self._meta.model is None:
            from journal.models import OwnerHistory

            self._meta.model = OwnerHistory


class PublisherHistoryForm(OrganizationMixin, CoreAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define o model dinamicamente para evitar importação circular
        if not hasattr(self._meta, "model") or self._meta.model is None:
            from journal.models import PublisherHistory

            self._meta.model = PublisherHistory


class SponsorHistoryForm(OrganizationMixin, CoreAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define o model dinamicamente para evitar importação circular
        if not hasattr(self._meta, "model") or self._meta.model is None:
            from journal.models import SponsorHistory

            self._meta.model = SponsorHistory


class CopyrightHolderHistoryForm(OrganizationMixin, CoreAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define o model dinamicamente para evitar importação circular
        if not hasattr(self._meta, "model") or self._meta.model is None:
            from journal.models import CopyrightHolderHistory

            self._meta.model = CopyrightHolderHistory


class SciELOJournalModelForm(CoreAdminModelForm):
    def save_all(self, user):
        instance_model = super().save_all(user)

        if self.instance.issn_scielo is None:
            self.instance.issn_scielo = (
                instance_model.journal.official.issn_electronic
                or instance_model.journal.official.issn_print
            )

        self.save()

        return instance_model
