# Generated by Django 4.2.7 on 2023-12-07 12:39

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("institution", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="InstitutionIdentification",
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
                ("name", models.TextField(blank=True, null=True, verbose_name="Nome")),
                (
                    "acronym",
                    models.TextField(
                        blank=True, null=True, verbose_name="Institution Acronym"
                    ),
                ),
                (
                    "is_official",
                    models.BooleanField(
                        blank=True, null=True, verbose_name="Is official"
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
                    "official",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="institution.institutionidentification",
                        verbose_name="Official name",
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
                    models.Index(fields=["name"], name="institution_name_8d98a7_idx"),
                    models.Index(
                        fields=["is_official"], name="institution_is_offi_96e102_idx"
                    ),
                ],
            },
        ),
    ]