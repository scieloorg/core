# Generated manually

import django.db.models.deletion
from django.db import migrations, models


def migrate_doi_prefix_to_crossref_configuration(apps, schema_editor):
    Journal = apps.get_model("journal", "Journal")
    CrossRefConfiguration = apps.get_model("doi_manager", "CrossRefConfiguration")

    for journal in Journal.objects.exclude(doi_prefix__isnull=True).exclude(doi_prefix=""):
        crossref_config, _ = CrossRefConfiguration.objects.get_or_create(
            prefix=journal.doi_prefix
        )
        journal.crossref_configuration = crossref_config
        journal.save(update_fields=["crossref_configuration"])


class Migration(migrations.Migration):

    dependencies = [
        ("doi_manager", "0003_alter_crossrefconfiguration_created_and_more"),
        ("journal", "0057_crossmarkpolicy"),
    ]

    operations = [
        migrations.AddField(
            model_name="journal",
            name="crossref_configuration",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="doi_manager.crossrefconfiguration",
                verbose_name="CrossRef Configuration",
            ),
        ),
        migrations.RunPython(
            migrate_doi_prefix_to_crossref_configuration,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="journal",
            name="doi_prefix",
        ),
    ]
