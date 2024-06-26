# Generated by Django 5.0.3 on 2024-05-28 15:21

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CrossRefConfiguration",
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
                    "prefix",
                    models.CharField(
                        blank=True, max_length=10, null=True, verbose_name="Prefix"
                    ),
                ),
                (
                    "depositor_name",
                    models.CharField(
                        blank=True,
                        max_length=64,
                        null=True,
                        verbose_name="Depositor Name",
                    ),
                ),
                (
                    "depositor_email_address",
                    models.EmailField(
                        blank=True,
                        max_length=64,
                        null=True,
                        verbose_name="Depositor e-mail",
                    ),
                ),
                (
                    "registrant",
                    models.CharField(
                        blank=True, max_length=64, null=True, verbose_name="Registrant"
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
    ]
