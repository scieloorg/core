import os

from django.db import models
from django.utils.translation import gettext as _
from core.models import CommonControlField
from wagtail.documents.edit_handlers import DocumentChooserPanel

from .forms import ThematicAreaForm, ThematicAreaFileForm
from . import choices


# Create your models here.
class ThematicArea(CommonControlField):
    """
    Represent the thematic areas wit 3 levels.

    Fields:
        level 0
        level 1
        level 2
    """

    level0 = models.CharField(_("Level 0"), choices=choices.thematic_level0,
                              max_length=255, null=True, blank=True,
                              help_text=_("Here the thematic colleges of CAPES must be registered, more about these areas access: https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/avaliacao/sobre-a-avaliacao/areas-avaliacao/sobre-as-areas-de-avaliacao/sobre-as-areas-de-avaliacao"))

    level1 = models.CharField(_("Level 1"), choices=choices.thematic_level1,
                              max_length=255, null=True, blank=True,
                              help_text=_("Here the thematic colleges of CAPES must be registered, more about these areas access: https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/avaliacao/sobre-a-avaliacao/areas-avaliacao/sobre-as-areas-de-avaliacao/sobre-as-areas-de-avaliacao"))

    level2 = models.CharField(_("Level 2"), choices=choices.thematic_level2,
                              max_length=255, null=True, blank=True,
                              help_text=_("Here the thematic colleges of CAPES must be registered, more about these areas access: https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/avaliacao/sobre-a-avaliacao/areas-avaliacao/sobre-as-areas-de-avaliacao/sobre-as-areas-de-avaliacao"))

    class Meta:
        verbose_name = _("Thematic Area")
        verbose_name_plural = _("Thematic Areas")

    def __unicode__(self):
        return u'%s | %s | %s' % (self.level0, self.level1, self.level2, )

    def __str__(self):
        return u'%s | %s | %s' % (self.level0, self.level1, self.level2, )

    @classmethod
    def get_or_create(cls, level0, level1, level2, user):
        try:
            return ThematicArea.objects.get(level0=level0, level1=level1, level2=level2)
        except ThematicArea.DoesNotExist:
            the_area = ThematicArea()
            the_area.level0 = level0
            the_area.level1 = level1
            the_area.level2 = level2
            the_area.creator = user
            the_area.save()

        return the_area

    base_form_class = ThematicAreaForm


class ThematicAreaFile(CommonControlField):
    class Meta:
        verbose_name_plural = _('Thematic Areas Upload')

    attachment = models.ForeignKey(
        'wagtaildocs.Document',
        verbose_name=_("Attachment"),
        null=True, blank=False,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    is_valid = models.BooleanField(_("Is valid?"), default=False, blank=True,
                                   null=True)
    line_count = models.IntegerField(_("Number of lines"), default=0,
                                     blank=True, null=True)

    def filename(self):
        return os.path.basename(self.attachment.name)

    panels = [
        DocumentChooserPanel('attachment')
    ]
    base_form_class = ThematicAreaFileForm
