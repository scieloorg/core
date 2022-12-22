from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import CommonControlField

from .forms import ProcessingErrorsForm


class ProcessingError(CommonControlField):
    item = models.CharField(_('Error item'), max_length=510, null=True, blank=True)
    description = models.CharField(_('Error description'), max_length=510, null=True, blank=True)
    type = models.CharField(_('Error type'), max_length=255, null=True, blank=True)
    step = models.CharField(_('Error occurrence step'), max_length=255, null=True, blank=True)

    base_form_class = ProcessingErrorsForm
