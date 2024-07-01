# Generated by Django 5.0.3 on 2024-07-01 04:23

import django.db.models.deletion
import modelcluster.fields
from django.conf import settings
from django.db import migrations, models


def transfer_journal_url_to_journal_urls_inline_panel(apps, schema_editor):
    Journal = apps.get_model('journal', 'Journal')
    JournalURL = apps.get_model('journal', 'JournalURL')

    journals_to_create = []
    for instance in Journal.objects.filter(journal_url__isnull=False):
        journals_to_create.append(JournalURL(journal=instance, url=instance.journal_url))
    
    if journals_to_create:
        JournalURL.objects.bulk_create(journals_to_create)


def reverse_transfer_journal_url_to_journal_urls_inline_panel(apps, schema_editor):
    JournalURL = apps.get_model('journal', 'JournalURL')
    JournalURL.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("journal", "0024_alter_officialjournal_issn_electronic_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="JournalURL",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Creation date"
                    ),
                ),
                (
                    "updated",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Last update date"
                    ),
                ),
                (
                    "url",
                    models.URLField(
                        blank=True,
                        help_text="If the journal is published in another site, enter in this field the other site location",
                        null=True,
                    ),
                ),
                (
                    "creator",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_creator",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Creator",
                    ),
                ),
                (
                    "journal",
                    modelcluster.fields.ParentalKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="related_journal_urls",
                        to="journal.journal",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_last_mod_user",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Updater",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.RunPython(
            transfer_journal_url_to_journal_urls_inline_panel,
            reverse_code=reverse_transfer_journal_url_to_journal_urls_inline_panel,
        )
    ]
