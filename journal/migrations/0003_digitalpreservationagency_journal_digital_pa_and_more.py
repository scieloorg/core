# Generated by Django 4.2.7 on 2024-01-05 14:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("journal", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DigitalPreservationAgency",
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
                ("name", models.TextField(blank=True, null=True, verbose_name="Name")),
                (
                    "acronym",
                    models.CharField(
                        blank=True, max_length=64, null=True, verbose_name="Acronym"
                    ),
                ),
                ("url", models.URLField(blank=True, null=True)),
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
                "verbose_name": "Digitial Preservation Agency",
                "verbose_name_plural": "Digital Preservation Agencies",
            },
        ),
        migrations.AddField(
            model_name="journal",
            name="digital_pa",
            field=models.ManyToManyField(
                blank=True,
                to="journal.digitalpreservationagency",
                verbose_name="DigitalPreservationAgency",
            ),
        ),
        migrations.AddIndex(
            model_name="digitalpreservationagency",
            index=models.Index(fields=["name"], name="journal_dig_name_fcaedb_idx"),
        ),
        migrations.AddIndex(
            model_name="digitalpreservationagency",
            index=models.Index(fields=["url"], name="journal_dig_url_a4154a_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="digitalpreservationagency",
            unique_together={("name", "acronym", "url")},
        ),
    ]
