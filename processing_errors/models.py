from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import CommonControlField

from .forms import ProcessingErrorsForm


class ProcessingError(CommonControlField):
    item = models.TextField(_('Error item'), null=True, blank=True)
    description = models.TextField(_('Error description'), null=True, blank=True)
    type_field = models.TextField(_('Error type'), null=True, blank=True)
    step = models.TextField(_('Error occurrence step'), null=True, blank=True)

    base_form_class = ProcessingErrorsForm
