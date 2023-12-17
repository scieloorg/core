# Generated by Django 4.2.7 on 2023-12-14 15:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DOI",
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
                    "value",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="Value"
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
                    "language",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="core.language",
                        verbose_name="Language",
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
        ),
        migrations.CreateModel(
            name="DOIRegistration",
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
                    "submission_date",
                    models.DateField(
                        blank=True,
                        max_length=20,
                        null=True,
                        verbose_name="Submission Date",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("DATA_CREATED", "DATA_CREATED"),
                            ("SUBMITTED", "SUBMITTED"),
                            ("QUEUED", "QUEUED"),
                            ("DEPOSITED", "DEPOSITED"),
                        ],
                        max_length=15,
                        null=True,
                        verbose_name="Status",
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
                    "doi",
                    models.ManyToManyField(
                        blank=True, to="doi.doi", verbose_name="DOI"
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
                "indexes": [
                    models.Index(
                        fields=["submission_date"],
                        name="doi_doiregi_submiss_6d5f36_idx",
                    ),
                    models.Index(
                        fields=["status"], name="doi_doiregi_status_bf6c24_idx"
                    ),
                ],
            },
        ),
        migrations.AddIndex(
            model_name="doi",
            index=models.Index(fields=["value"], name="doi_doi_value_58c508_idx"),
        ),
        migrations.AddIndex(
            model_name="doi",
            index=models.Index(fields=["language"], name="doi_doi_languag_804943_idx"),
        ),
    ]
