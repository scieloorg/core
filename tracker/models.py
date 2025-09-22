import json
import logging
import traceback
import uuid
from datetime import datetime

from django.core.files.base import ContentFile
from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField
from tracker import choices


class ProcEventCreateError(Exception): ...


class UnexpectedEventCreateError(Exception): ...


class EventCreateError(Exception): ...


class EventReportCreateError(Exception): ...


class EventReportSaveFileError(Exception): ...


class EventReportCreateError(Exception): ...


class EventReportDeleteEventsError(Exception): ...


class BaseEvent(models.Model):
    name = models.CharField(_("name"), max_length=200)
    detail = models.JSONField(null=True, blank=True)
    created = models.DateTimeField(verbose_name=_("Creation date"), auto_now_add=True)

    class Meta:
        abstract = True

    @property
    def data(self):
        return {
            "name": self.name,
            "detail": self.detail,
            "created": self.created.isoformat(),
        }

    @classmethod
    def create(
        cls,
        name=None,
        detail=None,
    ):
        obj = cls()
        obj.detail = detail
        obj.name = name
        obj.save()
        return obj


class UnexpectedEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(verbose_name=_("Creation date"), auto_now_add=True)
    exception_type = models.TextField(_("Exception Type"), null=True, blank=True)
    exception_msg = models.TextField(_("Exception Msg"), null=True, blank=True)
    traceback = models.JSONField(null=True, blank=True)
    detail = models.JSONField(null=True, blank=True)
    item = models.CharField(
        _("Item"),
        max_length=256,
        null=True,
        blank=True,
    )
    action = models.CharField(
        _("Action"),
        max_length=256,
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["exception_type"]),
            models.Index(fields=["item"]),
            models.Index(fields=["action"]),
        ]
        ordering = ["-created"]

    def __str__(self):
        if self.item or self.action:
            return f"{self.action} {self.item} {self.exception_msg}"
        return f"{self.exception_msg}"

    @property
    def data(self):
        return dict(
            created=self.created.isoformat(),
            item=self.item,
            action=self.action,
            exception_type=self.exception_type,
            exception_msg=self.exception_msg,
            traceback=json.dumps(self.traceback),
            detail=json.dumps(self.detail),
        )

    @classmethod
    def create(
        cls,
        exception=None,
        exc_traceback=None,
        item=None,
        action=None,
        detail=None,
    ):
        try:
            if exception:
                logging.exception(exception)

            obj = cls()
            obj.item = item
            obj.action = action
            obj.exception_msg = str(exception)
            obj.exception_type = str(type(exception))
            try:
                json.dumps(detail)
                obj.detail = detail
            except Exception as e:
                obj.detail = str(detail)

            if exc_traceback:
                obj.traceback = traceback.format_tb(exc_traceback)
            obj.save()
            return obj
        except Exception as exc:
            raise UnexpectedEventCreateError(
                f"Unable to create unexpected event ({exception} {exc_traceback}). EXCEPTION {exc}"
            )


def tracker_file_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>

    d = datetime.utcnow()
    return f"tracker/{d.year}/{d.month}/{d.day}/{filename}"


class Hello(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.BooleanField(null=True, blank=True, default=None)
    created = models.DateTimeField(verbose_name=_("Creation date"), auto_now_add=True)
    exception_type = models.TextField(_("Exception Type"), null=True, blank=True)
    exception_msg = models.TextField(_("Exception Msg"), null=True, blank=True)
    traceback = models.JSONField(null=True, blank=True)
    detail = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["exception_type"]),
        ]

    def __str__(self):
        return f"{self.status or self.exception_type} {self.created.isoformat()}"

    @property
    def data(self):
        return dict(
            status=self.status,
            created=self.created.isoformat(),
            exception_type=self.exception_type,
            exception_msg=self.exception_msg,
            traceback=json.dumps(self.traceback),
            detail=json.dumps(self.detail),
        )

    @classmethod
    def create(cls, exception=None, exc_traceback=None, detail=None, status=None):
        if exception:
            logging.exception(exception)

        obj = cls()
        obj.status = status or not exception and not exc_traceback
        obj.exception_msg = str(exception)
        obj.exception_type = str(type(exception))
        try:
            json.dumps(detail)
            obj.detail = detail
        except Exception as e:
            obj.detail = str(detail)

        if exc_traceback:
            obj.traceback = traceback.format_tb(exc_traceback)
        obj.save()
        return obj
