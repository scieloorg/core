from functools import partial

from django.db import migrations, models

from core.utils.legacy_record_unique import (
    add_unique_collection_pid,
    remove_unique_collection_pid,
)

PARAMS = dict(
    app_label="issue", model_name="AMIssue", name="unique_amissue_collection_pid"
)


class Migration(migrations.Migration):
    # remoção de duplicados em lotes e CREATE INDEX CONCURRENTLY (ver
    # core.utils.legacy_record_unique)
    atomic = False

    dependencies = [
        ("collection", "0001_initial"),
        ("issue", "0021_tableofcontents_journal_toc_and_more"),
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
                    model_name="amissue",
                    constraint=models.UniqueConstraint(
                        fields=("collection", "pid"),
                        name="unique_amissue_collection_pid",
                    ),
                ),
            ],
        ),
    ]
