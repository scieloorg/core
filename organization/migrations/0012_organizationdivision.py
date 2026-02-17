# Generated manually for OrganizationDivision model creation

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0011_convert_textfield_to_charfield"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OrganizationDivision",
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
                    "level_1",
                    models.CharField(
                        blank=True, max_length=255, null=True, verbose_name="Organization Level 1"
                    ),
                ),
                (
                    "level_2",
                    models.CharField(
                        blank=True, max_length=255, null=True, verbose_name="Organization Level 2"
                    ),
                ),
                (
                    "level_3",
                    models.CharField(
                        blank=True, max_length=255, null=True, verbose_name="Organization Level 3"
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
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="divisions",
                        to="organization.organization",
                        verbose_name="Organization",
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
                "verbose_name": "Organization Division",
                "verbose_name_plural": "Organization Divisions",
                "unique_together": {("level_1", "level_2", "level_3", "organization")},
            },
        ),
    ]
