# Generated by Django 4.2.7 on 2023-12-19 17:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MinioFile",
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
                    "basename",
                    models.TextField(blank=True, null=True, verbose_name="Basename"),
                ),
                ("uri", models.URLField(blank=True, null=True, verbose_name="URI")),
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
                "indexes": [
                    models.Index(
                        fields=["basename"], name="files_stora_basenam_9cfe44_idx"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="MinioConfiguration",
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
                ("name", models.TextField(null=True, verbose_name="Name")),
                ("host", models.TextField(blank=True, null=True, verbose_name="Host")),
                (
                    "bucket_root",
                    models.TextField(blank=True, null=True, verbose_name="Bucket root"),
                ),
                (
                    "bucket_app_subdir",
                    models.TextField(
                        blank=True, null=True, verbose_name="Bucket app subdir"
                    ),
                ),
                (
                    "access_key",
                    models.TextField(blank=True, null=True, verbose_name="Access key"),
                ),
                (
                    "secret_key",
                    models.TextField(blank=True, null=True, verbose_name="Secret key"),
                ),
                ("secure", models.BooleanField(default=True, verbose_name="Secure")),
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
                "indexes": [
                    models.Index(fields=["name"], name="files_stora_name_6664a8_idx"),
                    models.Index(fields=["host"], name="files_stora_host_12e098_idx"),
                    models.Index(
                        fields=["bucket_root"], name="files_stora_bucket__8a0a27_idx"
                    ),
                ],
            },
        ),
    ]
