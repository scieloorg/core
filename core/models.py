from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField

from . import choices

User = get_user_model()


class CommonControlField(models.Model):
    """
    Class with common control fields.

    Fields:
        created: Date time when the record was created
        updated: Date time with the last update date
        creator: The creator of the record
        updated_by: Store the last updator of the record
    """

    # Creation date
    created = models.DateTimeField(
        verbose_name=_("Creation date"), auto_now_add=True
    )

    # Update date
    updated = models.DateTimeField(
        verbose_name=_("Last update date"), auto_now=True
    )

    # Creator user
    creator = models.ForeignKey(
        User,
        verbose_name=_("Creator"),
        related_name="%(class)s_creator",
        editable=False,
        on_delete=models.SET_NULL,
        null=True,
    )

    # Last modifier user
    updated_by = models.ForeignKey(
        User,
        verbose_name=_("Updater"),
        related_name="%(class)s_last_mod_user",
        editable=False,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        abstract = True


class TextWithLang(models.Model):
    text = models.CharField(_('Text'), max_length=255, null=True, blank=True)
    language = models.CharField(_('Language'), max_length=2, choices=choices.LANGUAGE,
                                null=True, blank=True)

    panels = [
        FieldPanel('text'),
        FieldPanel('language')
    ]

    class Meta:
        abstract = True


class RichTextWithLang(models.Model):
    text = RichTextField(null=True, blank=True)
    language = models.CharField(_('Language'), max_length=2, choices=choices.LANGUAGE, null=True, blank=True)

    panels = [
        FieldPanel('text'),
        FieldPanel('language')
    ]

    class Meta:
        abstract = True


class FlexibleDate(models.Model):
    year = models.IntegerField(_('Year'), null=True, blank=True)
    month = models.IntegerField(_('Month'), null=True, blank=True)
    day = models.IntegerField(_('Day'), null=True, blank=True)

    def __unicode__(self):
        return u'%s/%s/%s' % (self.year, self.month, self.day)

    def __str__(self):
        return u'%s/%s/%s' % (self.year, self.month, self.day)

    @property
    def data(self):
        return dict(
            date__year=self.year,
            date__month=self.month,
            date__day=self.day,
        )
