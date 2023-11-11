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

    class Meta:
        indexes = [
            models.Index(fields=["exception_type"]),
        ]

    def __str__(self):
        return f"{self.exception_msg}"

    @property
    def data(self):
        return dict(
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
    ):
        try:
            if exception:
                logging.exception(exception)

            obj = cls()
            obj.exception_msg = exception
            obj.exception_type = type(exception)
            obj.detail = detail
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


# class EventLogger:

#     def archive_report(self, user, ext=None):
#         events = ProcEvent.objects.filter(proc_event_logger=self).iterator()
#         try:
#             obj = ProcEventReport.archive(user, events, ext)
#             obj.proc_event_logger = self
#             obj.save()
#         except Exception as e:
#             raise ArchiveProcEventReportError(
#                 f"Unable to archive events {self}. Exception: {e}"
#             )
#         return obj

#     def create_event(
#         self,
#         user,
#         message_type,
#         message=None,
#         e=None,
#         exc_traceback=None,
#         detail=None,
#     ):
#         try:
#             obj = ProcEvent.create(
#                 creator=user,
#                 message=message,
#                 message_type=message_type,
#                 detail=detail,
#                 exception=e,
#                 exc_traceback=exc_traceback,
#             )
#             obj.proc_event_logger = self
#             obj.save()
#         except Exception as exc:
#             raise ProcEventCreateError(
#                 f"Unable to create ProcEvent ({proc_event_logger} {message} {e}). EXCEPTION: {exc}")
#         return obj


# class ProcEventReport(EventReport, Orderable):
#     proc_event_logger = ParentalKey(
#         EventLogger, on_delete=models.SET_NULL, related_name="proc_event_file",
#         null=True, blank=True,
#     )

#     base_form_class = CoreAdminModelForm

#     panels = [
#         # FieldPanel("created"),
#         FieldPanel("file"),
#     ]

#     # @classmethod
#     # def archive_with_parent(cls, user, proc_event_logger, events, ext=None):
#     #     obj = cls.archive(user, events, ext)
#     #     obj.proc_event_logger = proc_event_logger
#     #     obj.save()
#     #     return obj


# class ProcEvent(Event, Orderable):
#     event_parent = ParentalKey(
#         EventLogger, on_delete=models.SET_NULL, related_name="proc_event",
#         null=True, blank=True,
#     )

#     base_form_class = CoreAdminModelForm

#     panels = [
#         # FieldPanel("created"),
#         FieldPanel("message"),
#         FieldPanel("message_type"),
#         FieldPanel("detail"),
#         FieldPanel("unexpected_event"),
#     ]

#     # @classmethod
#     # def create_with_parent(
#     #     cls,
#     #     user,
#     #     proc_event_logger,
#     #     message_type,
#     #     message=None,
#     #     e=None,
#     #     exc_traceback=None,
#     #     detail=None,
#     # ):
#     #     try:
#     #         obj = cls.create(
#     #             creator=user,
#     #             message=message,
#     #             message_type=message_type,
#     #             detail=detail,
#     #             exception=e,
#     #             exc_traceback=exc_traceback,
#     #         )
#     #         obj.proc_event_logger = proc_event_logger
#     #         obj.save()
#     #     except Exception as exc:
#     #         raise ProcEventCreateError(
#     #             f"Unable to create Event ({proc_event_logger} {message} {e}). EXCEPTION: {exc}")
#     #     return obj
