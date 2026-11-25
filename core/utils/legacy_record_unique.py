"""
Garante, por migração, um único registro legado (AMJournal, AMIssue) por
(collection, pid), em tabelas grandes e com a coleta em andamento.

Decisões:
- a migração não é atômica: a remoção de duplicados é feita em lotes, cada um
  em sua transação, para não manter locks nem estourar statement_timeout
- o índice único é criado com CREATE INDEX CONCURRENTLY (sem bloquear escrita);
  se a coleta inserir um duplicado durante a criação, o índice fica inválido:
  é removido, os duplicados são removidos de novo e a criação é repetida
- a restrição é anexada ao índice já pronto (ADD CONSTRAINT ... USING INDEX),
  operação rápida, com lock_timeout para não enfileirar a coleta atrás dela
- o registro mantido é o migrado (data / url), associado a um registro novo e
  mais recente; se não estiver associado, herda a associação de um duplicado
  migrado
"""

import logging
import time

from django.db import IntegrityError, OperationalError, models, transaction
from django.db.models import BooleanField, Count, ExpressionWrapper, Q

BATCH_SIZE = 500
ATTEMPTS = 5
LOCK_TIMEOUT = "5s"
RETRY_WAIT = 5

logger = logging.getLogger(__name__)


def _preference(item):
    return (
        item["has_data"],
        bool(item["url"]),
        bool(item.get("new_record_id")),
        item["updated"] or item["created"],
        item["id"],
    )


def _remove_duplicates_of(model, collection_id, pid, has_new_record):
    fields = ["id", "url", "updated", "created"]
    if has_new_record:
        fields.append("new_record_id")
    items = sorted(
        model.objects.filter(collection_id=collection_id, pid=pid)
        .annotate(
            has_data=ExpressionWrapper(Q(data__isnull=False), BooleanField())
        )
        .values("has_data", *fields),
        key=_preference,
        reverse=True,
    )
    if len(items) < 2:
        return 0
    keep, duplicates = items[0], items[1:]
    if has_new_record and not keep["new_record_id"]:
        for item in duplicates:
            if item["new_record_id"] and (item["has_data"] or item["url"]):
                model.objects.filter(pk=keep["id"]).update(
                    new_record_id=item["new_record_id"]
                )
                break
    model.objects.filter(pk__in=[item["id"] for item in duplicates]).delete()
    return len(duplicates)


def remove_duplicates(model, using="default", batch_size=BATCH_SIZE):
    has_new_record = any(field.name == "new_record" for field in model._meta.fields)
    keys = list(
        model.objects.using(using)
        .filter(pid__isnull=False, collection__isnull=False)
        .values("collection_id", "pid")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
        .values_list("collection_id", "pid")
    )
    removed = 0
    for start in range(0, len(keys), batch_size):
        with transaction.atomic(using=using):
            for collection_id, pid in keys[start : start + batch_size]:
                removed += _remove_duplicates_of(
                    model, collection_id, pid, has_new_record
                )
    logger.info(f"{model.__name__}: {removed} duplicated records removed")
    return removed


def _constraint_exists(cursor, name):
    cursor.execute("SELECT 1 FROM pg_constraint WHERE conname = %s", [name])
    return cursor.fetchone() is not None


def add_unique_collection_pid(apps, schema_editor, app_label, model_name, name):
    model = apps.get_model(app_label, model_name)
    connection = schema_editor.connection
    using = connection.alias

    if connection.vendor != "postgresql":
        remove_duplicates(model, using)
        schema_editor.add_constraint(
            model, models.UniqueConstraint(fields=["collection", "pid"], name=name)
        )
        return

    quote_name = schema_editor.quote_name
    table = model._meta.db_table
    with connection.cursor() as cursor:
        if _constraint_exists(cursor, name):
            return
        # sem limite para as operações longas (deduplicação e índice);
        # cada uma é curta em lock, não em duração
        cursor.execute("SET statement_timeout = 0")
        try:
            for attempt in range(ATTEMPTS):
                remove_duplicates(model, using)
                cursor.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {quote_name(name)}")
                try:
                    cursor.execute(
                        f"CREATE UNIQUE INDEX CONCURRENTLY {quote_name(name)} "
                        f"ON {quote_name(table)} (collection_id, pid)"
                    )
                    break
                except IntegrityError:
                    # duplicado inserido durante a criação: índice inválido
                    logger.warning(
                        f"{table}: duplicated records inserted while creating "
                        f"{name} (attempt {attempt + 1}), retrying"
                    )
            else:
                raise IntegrityError(
                    f"Unable to create unique index {name} on {table}: "
                    f"duplicated records keep being inserted"
                )

            for attempt in range(ATTEMPTS):
                try:
                    with transaction.atomic(using=using):
                        cursor.execute(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'")
                        cursor.execute(
                            f"ALTER TABLE {quote_name(table)} "
                            f"ADD CONSTRAINT {quote_name(name)} "
                            f"UNIQUE USING INDEX {quote_name(name)}"
                        )
                    return
                except OperationalError:
                    # lock não obtido a tempo: tabela em uso pela coleta
                    logger.warning(
                        f"{table}: lock timeout adding {name} "
                        f"(attempt {attempt + 1}), retrying"
                    )
                    time.sleep(RETRY_WAIT)
            raise OperationalError(f"Unable to lock {table} to add {name}")
        finally:
            cursor.execute("RESET statement_timeout")


def remove_unique_collection_pid(apps, schema_editor, app_label, model_name, name):
    model = apps.get_model(app_label, model_name)
    schema_editor.execute(
        f"ALTER TABLE {schema_editor.quote_name(model._meta.db_table)} "
        f"DROP CONSTRAINT IF EXISTS {schema_editor.quote_name(name)}"
    )
