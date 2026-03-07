from django import forms
from django.utils.translation import gettext_lazy as _

from .models import CrossRefConfiguration


class CrossRefConfigurationForm(forms.ModelForm):
    class Meta:
        model = CrossRefConfiguration
        fields = [
            "depositor_name",
            "depositor_email_address",
            "registrant",
            "prefix",
            "password",
        ]
        widgets = {
            "password": forms.PasswordInput(),
        }
