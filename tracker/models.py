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


class ProcEventCreateError(Exception):
    ...


class UnexpectedEventCreateError(Exception):
    ...


class EventCreateError(Exception):
    ...


class EventReportCreateError(Exception):
    ...


class EventReportSaveFileError(Exception):
    ...


class EventReportCreateError(Exception):
    ...


class EventReportDeleteEventsError(Exception):
    ...


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


class Event(CommonControlField):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.TextField(_("Message"), null=True, blank=True)
    message_type = models.CharField(
        _("Message type"),
        choices=choices.EVENT_MSG_TYPE,
        max_length=16,
        null=True,
        blank=True,
    )
    detail = models.JSONField(null=True, blank=True)
    unexpected_event = models.ForeignKey(
        UnexpectedEvent, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["message_type"]),
        ]

    @property
    def data(self):
        d = {}
        d["created"] = self.created.isoformat()
        d["user"] = self.user.username
        d.update(
            dict(
                message=self.message, message_type=self.message_type, detail=self.detail
            )
        )
        if self.unexpected_event:
            d.update(self.unexpected_event.data)
        return d

    @classmethod
    def create(
        cls,
        user=None,
        message_type=None,
        message=None,
        e=None,
        exc_traceback=None,
        detail=None,
    ):
        try:
            obj = cls()
            obj.creator = user
            obj.message = message
            obj.message_type = message_type
            obj.detail = detail
            obj.save()

            if e:
                logging.exception(f"{message}: {e}")
                obj.unexpected_event = UnexpectedEvent.create(
                    exception=e,
                    exc_traceback=exc_traceback,
                )
                obj.save()
        except Exception as exc:
            raise EventCreateError(
                f"Unable to create Event ({message} {e}). EXCEPTION: {exc}"
            )
        return obj


def tracker_file_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>

    d = datetime.utcnow()
    return f"tracker/{d.year}/{d.month}/{d.day}/{filename}"


class EventReport(CommonControlField):
    file = models.FileField(
        upload_to=tracker_file_directory_path, null=True, blank=True
    )

    class Meta:
        abstract = True

    def save_file(self, events, ext=None):
        if not events:
            return
        try:
            ext = ".json"
            content = json.dumps(list([item.data for item in events]))
            name = datetime.utcnow().isoformat() + ext
            self.file.save(name, ContentFile(content))
            self.delete_events(events)
        except Exception as e:
            raise EventReportSaveFileError(
                f"Unable to save EventReport.file ({name}). Exception: {e}"
            )

    def delete_events(self, events):
        for item in events:
            try:
                item.unexpected_event.delete()
            except:
                pass
            try:
                item.delete()
            except:
                pass

    @classmethod
    def create(cls, user):
        try:
            obj = cls()
            obj.creator = user
            obj.save()
        except Exception as e:
            raise EventReportCreateError(
                f"Unable to create EventReport. Exception: {e}"
            )


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
    def create(
        cls,
        exception=None,
        exc_traceback=None,
        detail=None,
        status=None
    ):
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
