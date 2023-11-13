import csv
import os

from django.db import models
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField, Language

from . import choices


class GenericThematicArea(CommonControlField):
    text = models.TextField(_("Thematic Area"), null=True, blank=True)
    language = models.ForeignKey(
        Language,
        on_delete=models.SET_NULL,
        verbose_name=_("Language"),
        null=True,
        blank=True,
    )
    origin = models.TextField(_("Origin Data Base"), null=True, blank=True)
    level = models.CharField(
        _("Level"), choices=choices.levels, max_length=20, null=True, blank=True
    )
    level_up = models.ForeignKey(
        "GenericThematicArea",
        related_name="generic_thematic_area_level_up",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Generic Thematic Area")
        verbose_name_plural = _("Generic Thematic Areas")
        indexes = [
            models.Index(
                fields=[
                    "text",
                ]
            ),
            models.Index(
                fields=[
                    "origin",
                ]
            ),
            models.Index(
                fields=[
                    "level",
                ]
            ),
        ]

    def __unicode__(self):
        return "%s" % (self.text,)

    def __str__(self):
        return "%s" % (self.text,)

    @classmethod
    def get_or_create(cls, text, language, origin, level, level_up, user):
        try:
            return GenericThematicArea.objects.get(
                text=text,
                language=language,
                origin=origin,
                level=level,
                level_up=level_up,
            )
        except GenericThematicArea.DoesNotExist:
            the_area = GenericThematicArea()
            the_area.text = text
            the_area.language = language
            the_area.origin = origin
            the_area.level = level
            the_area.level_up = level_up
            the_area.creator = user
            the_area.save()

        return the_area

    base_form_class = CoreAdminModelForm


class GenericThematicAreaFile(CommonControlField):
    attachment = models.ForeignKey(
        "wagtaildocs.Document",
        verbose_name=_("Attachment"),
        on_delete=models.SET_NULL,
        null=True,
        blank=False,
        related_name="+",
    )
    is_valid = models.BooleanField(
        _("Is valid?"),
        default=False,
        blank=True,
        null=True,
    )
    line_count = models.IntegerField(
        _("Number of lines"),
        default=0,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name_plural = _("Generic Thematic Areas Upload")

    def filename(self):
        return os.path.basename(self.attachment.name)

    panels = [FieldPanel("attachment")]
    base_form_class = CoreAdminModelForm


class ThematicArea(CommonControlField):
    """
    Represent the thematic areas wit 3 levels.

    Fields:
        level 0
        level 1
        level 2
    """

    level0 = models.TextField(
        _("Level 0"),
        choices=choices.thematic_level0,
        blank=True,
        null=True,
        help_text=_(
            "Here the thematic colleges of CAPES must be registered, more about these areas access: https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/avaliacao/sobre-a-avaliacao/areas-avaliacao/sobre-as-areas-de-avaliacao/sobre-as-areas-de-avaliacao"
        ),
    )

    level1 = models.TextField(
        _("Level 1"),
        choices=choices.thematic_level1,
        blank=True,
        null=True,
        help_text=_(
            "Here the thematic colleges of CAPES must be registered, more about these areas access: https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/avaliacao/sobre-a-avaliacao/areas-avaliacao/sobre-as-areas-de-avaliacao/sobre-as-areas-de-avaliacao"
        ),
    )

    level2 = models.TextField(
        _("Level 2"),
        choices=choices.thematic_level2,
        blank=True,
        null=True,
        help_text=_(
            "Here the thematic colleges of CAPES must be registered, more about these areas access: https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/avaliacao/sobre-a-avaliacao/areas-avaliacao/sobre-as-areas-de-avaliacao/sobre-as-areas-de-avaliacao"
        ),
    )

    class Meta:
        verbose_name = _("Thematic Area")
        verbose_name_plural = _("Thematic Areas")
        indexes = [
            models.Index(
                fields=[
                    "level0",
                ]
            ),
            models.Index(
                fields=[
                    "level1",
                ]
            ),
            models.Index(
                fields=[
                    "level2",
                ]
            ),            
        ]

    def __unicode__(self):
        return "%s | %s | %s" % (
            self.level0,
            self.level1,
            self.level2,
        )

    def __str__(self):
        return "%s | %s | %s" % (
            self.level0,
            self.level1,
            self.level2,
        )

    @classmethod
    def load(cls, user, thematic_area_data=None):
        if thematic_area_data or not cls.objects.exists():
            thematic_area_data = thematic_area_data or "./thematic_areas/fixtures/thematic_areas.csv"
            with open(thematic_area_data, "r") as csvfile:
                reader = csv.DictReader(csvfile, fieldnames=["level0", "level1", "level2"], delimiter=";")
                for row in reader:
                    cls.get_or_create(
                        level0=row["level0"],
                        level1=row["level1"],
                        level2=row["level2"],
                        user=user,
                    )

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

    base_form_class = CoreAdminModelForm


class ThematicAreaFile(CommonControlField):
    attachment = models.ForeignKey(
        "wagtaildocs.Document",
        verbose_name=_("Attachment"),
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    is_valid = models.BooleanField(_("Is valid?"), default=False, blank=True, null=True)
    line_count = models.IntegerField(
        _("Number of lines"), default=0, blank=True, null=True
    )

    class Meta:
        verbose_name_plural = _("Thematic Areas Upload")

    def filename(self):
        return os.path.basename(self.attachment.name)

    panels = [FieldPanel("attachment")]
    base_form_class = CoreAdminModelForm
