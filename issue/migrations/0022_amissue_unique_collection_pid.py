from django.db import migrations, models

from core.utils.legacy_record_unique import (
    add_unique_collection_pid,
    remove_unique_collection_pid,
)

NAME = "issue_amissue_unique_collection_pid"


def forward(apps, schema_editor):
    add_unique_collection_pid(apps, schema_editor, "issue", "AMIssue", NAME)


def backward(apps, schema_editor):
    remove_unique_collection_pid(apps, schema_editor, "issue", "AMIssue", NAME)


class Migration(migrations.Migration):
    # remoção de duplicados em lotes e CREATE INDEX CONCURRENTLY
    # não podem rodar numa única transação
    atomic = False

    dependencies = [
        ("issue", "0021_tableofcontents_journal_toc_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddConstraint(
                    model_name="amissue",
                    constraint=models.UniqueConstraint(
                        fields=["collection", "pid"],
                        name=NAME,
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(forward, backward),
            ],
        ),
    ]
