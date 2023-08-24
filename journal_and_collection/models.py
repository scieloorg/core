from django.db import models
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from collection.models import Collection
from core.forms import CoreAdminModelForm
from core.models import CommonControlField
from journal.models import SciELOJournal

from . import choices


class Event(CommonControlField):
    collection = models.ForeignKey(
        Collection,
        verbose_name=_("Collection"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    occurrence_date = models.DateField(_("Occurrence date"), null=True, blank=True)
    occurrence_type = models.CharField(
        _("Occurrence type"),
        choices=choices.events,
        max_length=20,
        null=True,
        blank=True,
    )

    autocomplete_search_field = "collection__main_name"

    def autocomplete_label(self):
        return str(self)

    panels = [
        AutocompletePanel("collection"),
        FieldPanel("occurrence_date"),
        FieldPanel("occurrence_type"),
    ]

    class Meta:
        verbose_name = _("Event")
        verbose_name_plural = _("Events")
        indexes = [
            models.Index(
                fields=[
                    "occurrence_type",
                ]
            ),
        ]

    @property
    def data(self):
        d = {
            "event__occurrence_date": self.occurrence_date,
            "event__occurrence_type": self.occurrence_type,
        }

        if self.collection:
            d.update(self.collection.data)

        return d

    def __unicode__(self):
        return "%s in the %s in %s" % (
            self.occurrence_type,
            self.collection,
            str(self.occurrence_date),
        )

    def __str__(self):
        return "%s in the %s in %s" % (
            self.occurrence_type,
            self.collection,
            str(self.occurrence_date),
        )

    base_form_class = CoreAdminModelForm


class JournalAndCollection(CommonControlField):
    journal = models.ForeignKey(
        SciELOJournal,
        verbose_name=_("Journal"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    events_collection = models.ManyToManyField(
        Event, verbose_name=_("Events"), blank=True
    )

    panels = [
        AutocompletePanel("journal"),
        AutocompletePanel("events_collection"),
    ]

    class Meta:
        verbose_name = _("Journal and Collection")
        verbose_name_plural = _("Journals and Collections")

    @property
    def data(self):
        d = {}
        if self.journal:
            d.update(self.journal.data)
        if self.events_collection:
            events = [event.data for event in self.events_collection.iterator()]
            d.update({"journal_and_collection__event_collection": events})

        return d

    def __unicode__(self):
        return "%s" % self.journal

    def __str__(self):
        return "%s" % self.journal

    base_form_class = CoreAdminModelForm
