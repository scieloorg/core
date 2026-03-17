"""
Custom PostgreSQL database backend that combines:
- Connection pooling from django-db-connection-pool (SQLAlchemy QueuePool)
- Prometheus metrics from django-prometheus

This backend inherits from both mixins so that connections are managed
by a pool while still being tracked by Prometheus.
"""

from dj_db_conn_pool.backends.postgresql.mixins import PGDatabaseWrapperMixin
from django_prometheus.db.backends.postgresql.base import (
    DatabaseWrapper as PrometheusDatabaseWrapper,
)


class DatabaseWrapper(PGDatabaseWrapperMixin, PrometheusDatabaseWrapper):
    """
    PostgreSQL backend with connection pooling and Prometheus monitoring.

    MRO: PGDatabaseWrapperMixin is first so its get_new_connection() manages
    the SQLAlchemy QueuePool. When the pool needs a new connection, it calls
    through to PrometheusDatabaseWrapper which adds metrics tracking.
    """

    pass
