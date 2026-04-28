"""
Custom logging handlers for the SciELO Content Manager.

This module provides an OpenSearch logging handler that ships log records
to an OpenSearch cluster. It is intentionally tolerant of failures: any
error while contacting OpenSearch is suppressed (and reported to
``sys.stderr`` via ``logging.Handler.handleError``) so that logging never
disrupts the application.

Activation is controlled by the project's ``LOGGING`` configuration; when
OpenSearch is not enabled, loggers fall back to the console handler.

Usage from application code
---------------------------

The handler is wired in ``config/settings/*.py`` and attached to the root
and ``django`` loggers automatically when enabled, so application code
just uses the standard :mod:`logging` API. Both plain messages and
structured fields are supported:

.. code-block:: python

    import logging

    logger = logging.getLogger(__name__)

    # Plain message — indexed with the default fields (@timestamp, level,
    # logger, message, module, func_name, line_no, host, service,
    # environment, ...).
    logger.info("user logged in")

    # Message with positional arguments (Python's standard interpolation).
    logger.warning("slow query took %.2fs on table=%s", 1.23, "article")

    # Structured/contextual fields via ``extra={...}``. Any keys passed in
    # ``extra`` that are not standard ``LogRecord`` attributes are added
    # as top-level fields on the OpenSearch document, which makes them
    # filterable in dashboards (e.g. by ``user_id`` or ``request_id``).
    logger.info(
        "imported article",
        extra={
            "user_id": user.id,
            "article_pid": article.pid,
            "request_id": request_id,
            "duration_ms": duration_ms,
        },
    )

    # Exceptions are captured automatically with a full traceback when
    # ``exc_info=True`` (or when using ``logger.exception(...)`` inside
    # an ``except`` block).
    try:
        do_something()
    except Exception:
        logger.exception(
            "import failed",
            extra={"article_pid": pid, "stage": "xml_parse"},
        )

The ``service`` and ``environment`` fields (configured globally via
``OPENSEARCH_LOGGING_ENVIRONMENT`` in settings) are merged into every
document, so each environment writes to a clearly identified, separate
index (e.g. ``core-logs-prod-YYYY.MM.DD`` vs ``core-logs-dev-YYYY.MM.DD``)
and also carries the ``environment`` field inside the document itself.
"""
from __future__ import annotations

import atexit
import logging
import queue
import socket
import threading
from datetime import datetime, timezone
from typing import Any, Iterable, Optional


class OpenSearchLogHandler(logging.Handler):
    """A non-blocking logging handler that ships records to OpenSearch.

    Records are placed on an in-memory queue and shipped by a background
    daemon thread using ``opensearch-py``. The handler never raises:
    connection or indexing errors are routed through
    :meth:`logging.Handler.handleError` so the application is never
    impacted by logging failures.

    Parameters
    ----------
    hosts:
        Iterable of hosts (strings such as ``"https://os.example.org:9200"``
        or dicts accepted by :class:`opensearchpy.OpenSearch`). When empty
        or ``None`` the handler is a no-op.
    index:
        Index name (or index name prefix when ``index_date_format`` is
        set) used to store the log documents.
    index_date_format:
        Optional ``strftime`` format string. When set, the daily/monthly
        index name is built as
        ``f"{index}-{datetime.now(timezone.utc):format}"``.
    http_auth:
        Optional ``(user, password)`` tuple used for basic auth.
    use_ssl:
        Whether to use HTTPS (default ``True``).
    verify_certs:
        Whether to verify TLS certificates (default ``True``).
    extra_fields:
        Optional mapping merged into every log document (useful for
        environment / service tags).
    queue_size:
        Maximum number of buffered records. Older records are dropped
        when the queue is full to protect application memory.
    level:
        Standard ``logging`` level threshold.
    """

    def __init__(
        self,
        hosts: Optional[Iterable[Any]] = None,
        index: str = "scielo-core-logs",
        index_date_format: Optional[str] = "%Y.%m.%d",
        http_auth: Optional[tuple] = None,
        use_ssl: bool = True,
        verify_certs: bool = True,
        extra_fields: Optional[dict] = None,
        queue_size: int = 10_000,
        level: int = logging.NOTSET,
    ) -> None:
        super().__init__(level=level)
        self._hosts = list(hosts) if hosts else []
        self._index = index
        self._index_date_format = index_date_format
        self._http_auth = tuple(http_auth) if http_auth else None
        self._use_ssl = use_ssl
        self._verify_certs = verify_certs
        self._extra_fields = dict(extra_fields or {})
        self._hostname = socket.gethostname()

        self._queue: "queue.Queue[Optional[logging.LogRecord]]" = queue.Queue(
            maxsize=queue_size
        )
        self._client = None
        self._client_lock = threading.Lock()
        self._worker: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        if self._hosts:
            self._start_worker()
            atexit.register(self.close)

    # ------------------------------------------------------------------
    # Worker / client lifecycle
    # ------------------------------------------------------------------
    def _start_worker(self) -> None:
        self._worker = threading.Thread(
            target=self._run,
            name="OpenSearchLogHandler",
            daemon=True,
        )
        self._worker.start()

    def _get_client(self):
        if self._client is not None:
            return self._client
        with self._client_lock:
            if self._client is None:
                # Imported lazily so that environments without opensearch-py
                # installed can still import this module (the handler will
                # simply be inactive when no hosts are configured).
                from opensearchpy import OpenSearch  # type: ignore

                self._client = OpenSearch(
                    hosts=self._hosts,
                    http_auth=self._http_auth,
                    use_ssl=self._use_ssl,
                    verify_certs=self._verify_certs,
                    ssl_show_warn=self._verify_certs,
                )
        return self._client

    def _index_name(self) -> str:
        if not self._index_date_format:
            return self._index
        suffix = datetime.now(timezone.utc).strftime(self._index_date_format)
        return f"{self._index}-{suffix}"

    # ------------------------------------------------------------------
    # logging.Handler API
    # ------------------------------------------------------------------
    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        if not self._hosts:
            return
        try:
            self._queue.put_nowait(record)
        except queue.Full:
            # Drop the record rather than block the application thread.
            pass
        except Exception:
            self.handleError(record)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                record = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if record is None:  # sentinel from close()
                self._queue.task_done()
                break
            try:
                self._ship(record)
            except Exception:
                self.handleError(record)
            finally:
                self._queue.task_done()

    def _ship(self, record: logging.LogRecord) -> None:
        client = self._get_client()
        document = self._build_document(record)
        client.index(index=self._index_name(), body=document)

    # The standard attributes set by ``logging.LogRecord.__init__``. Any
    # attribute on the record that is *not* in this set has been supplied
    # by the caller via ``extra={...}`` and is therefore promoted to a
    # top-level field on the OpenSearch document.
    _RESERVED_RECORD_ATTRS = frozenset(
        {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "asctime", "taskName",
        }
    )

    def _build_document(self, record: logging.LogRecord) -> dict:
        try:
            message = record.getMessage()
        except Exception:
            message = record.msg if isinstance(record.msg, str) else repr(record.msg)
        document: dict = {
            "@timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "module": record.module,
            "func_name": record.funcName,
            "line_no": record.lineno,
            "process": record.process,
            "thread": record.thread,
            "host": self._hostname,
        }
        if record.exc_info:
            document["exception"] = self.format(
                logging.LogRecord(
                    name=record.name,
                    level=record.levelno,
                    pathname=record.pathname,
                    lineno=record.lineno,
                    msg="",
                    args=None,
                    exc_info=record.exc_info,
                )
            )
        # Promote any caller-supplied ``extra={...}`` keys to top-level
        # fields so they become filterable/searchable in OpenSearch.
        for key, value in record.__dict__.items():
            if key in self._RESERVED_RECORD_ATTRS or key.startswith("_"):
                continue
            document.setdefault(key, value)
        if self._extra_fields:
            for key, value in self._extra_fields.items():
                document.setdefault(key, value)
        return document

    def close(self) -> None:
        if self._stop_event.is_set():
            return
        self._stop_event.set()
        try:
            # Sentinel to wake the worker if it's blocked on the queue.
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._worker is not None and self._worker.is_alive():
            self._worker.join(timeout=2.0)
        super().close()
