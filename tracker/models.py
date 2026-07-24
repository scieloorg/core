import json
import logging
import traceback
import uuid
from datetime import datetime

from django.db import models
from django.utils.translation import gettext_lazy as _


class ProcEventCreateError(Exception): ...


class UnexpectedEventCreateError(Exception): ...


class EventCreateError(Exception): ...


class EventReportSaveFileError(Exception): ...


class EventReportCreateError(Exception): ...


class EventReportDeleteEventsError(Exception): ...


class EventSaveError(Exception): ...


class BaseEvent(models.Model):
    name = models.CharField(_("name"), max_length=200)
    detail = models.JSONField(null=True, blank=True)
    created = models.DateTimeField(verbose_name=_("Creation date"), auto_now_add=True)
    completed = models.BooleanField(default=False)

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

    def finish(self, completed=None, detail=None, errors=None, exceptions=None):
        try:
            completed = True
            detail = detail or {}
            if errors:
                detail["errors"] = errors
                completed = False
            if exceptions:
                detail["exceptions"] = exceptions
                completed = False
            self.completed = completed
            try:
                json.dumps(detail)
                self.detail = detail
            except Exception as e:
                logging.info(f"detail {detail}")
                self.detail = str(detail)
            self.save()
        except Exception as e:
            logging.exception(f"Error finishing BaseEvent: {e}")
            raise EventSaveError(f"Unable to create base event: {e}")


class UnexpectedEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(verbose_name=_("Creation date"), auto_now_add=True)
    updated = models.DateTimeField(verbose_name=_("Last update date"), auto_now=True)
    exception_type = models.CharField(_("Exception Type"), max_length=100, null=True, blank=True)
    exception_msg = models.CharField(_("Exception Msg"), max_length=400, null=True, blank=True)
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
        ordering = ["-updated", "-created"]

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
        """
        Cria um novo UnexpectedEvent ou atualiza um já existente
        (mesmo item + action, incluindo o par None/None), usando o
        mais recente em caso de múltiplos registros.
        """
        try:
            if exception:
                logging.exception(exception)

            obj = cls._get(item, action)

            if obj is not None:
                obj._update(exception, exc_traceback, item, action, detail)
            else:
                obj = cls._create(exception, exc_traceback, item, action, detail)

            obj.save()
            return obj
        except Exception as exc:
            raise UnexpectedEventCreateError(
                f"Unable to create unexpected event ({exception} {exc_traceback}). EXCEPTION {exc}"
            )

    # ------------------------------------------------------------------
    # Métodos auxiliares
    # ------------------------------------------------------------------

    @classmethod
    def _get(cls, item, action):
        """
        Busca um registro existente com o mesmo item e action
        (incluindo o par None, None). Se houver múltiplos, retorna
        o mais recente considerando updated e, em seguida, created.
        """
        qs = cls.objects.filter(item=item, action=action).order_by(
            "-updated", "-created"
        )
        return qs.first()

    def _update(self, exception, exc_traceback, item, action, detail):
        """
        Preenche/atualiza os campos do objeto (usado tanto na criação
        quanto na atualização).
        """
        self.item = item
        self.action = action
        self.exception_msg = str(exception)
        self.exception_type = str(type(exception))
        try:
            json.dumps(detail)
            self.detail = detail
        except Exception:
            self.detail = str(detail)

        if exc_traceback:
            self.traceback = traceback.format_tb(exc_traceback)

    @classmethod
    def _create(cls, exception, exc_traceback, item, action, detail):
        obj = cls()
        obj._update(exception, exc_traceback, item, action, detail)
        return obj


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
