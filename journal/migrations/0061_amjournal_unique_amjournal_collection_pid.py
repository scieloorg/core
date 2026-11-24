from functools import partial

from django.db import migrations, models

from core.utils.legacy_record_unique import (
    add_unique_collection_pid,
    remove_unique_collection_pid,
)

PARAMS = dict(
    app_label="journal", model_name="AMJournal", name="unique_amjournal_collection_pid"
)


class Migration(migrations.Migration):
    # remoção de duplicados em lotes e CREATE INDEX CONCURRENTLY (ver
    # core.utils.legacy_record_unique)
    atomic = False

    dependencies = [
        ("collection", "0001_initial"),
        ("journal", "0060_alter_journalparalleltitle_unique_together"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    partial(add_unique_collection_pid, **PARAMS),
                    partial(remove_unique_collection_pid, **PARAMS),
                ),
            ],
            state_operations=[
                migrations.AddConstraint(
                    model_name="amjournal",
                    constraint=models.UniqueConstraint(
                        fields=("collection", "pid"),
                        name="unique_amjournal_collection_pid",
                    ),
                ),
            ],
        ),
    ]
