# Generated by Django 4.1.8 on 2023-07-18 23:55

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("researcher", "0007_alter_researcher_gender_identification_status_and_more"),
        ("institution", "0003_alter_institution_acronym_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        (
            "vocabulary",
            "0004_rename_vocabulary__languag_a11f3d_idx_vocabulary__languag_479020_idx_and_more",
        ),
        ("issue", "0008_remove_bibliographicstrip_subtitle_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Affliation",
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
                ("name", models.TextField(blank=True, null=True)),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="researcher.researcher",
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
        migrations.CreateModel(
            name="Dataset",
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
                ("name", models.TextField(blank=True, null=True)),
                (
                    "type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("dataverse", "dataverse"),
                            ("dataset", "dataset"),
                            ("file", "file"),
                        ],
                        max_length=9,
                        null=True,
                    ),
                ),
                ("url", models.URLField(blank=True, null=True, verbose_name="URL")),
                (
                    "published_at",
                    models.CharField(blank=True, max_length=25, null=True),
                ),
                ("global_id", models.CharField(blank=True, max_length=100, null=True)),
                ("description", models.TextField(blank=True, null=True)),
                ("citation_html", models.TextField(blank=True, null=True)),
                ("citation", models.TextField(blank=True, null=True)),
                (
                    "authors",
                    models.ManyToManyField(blank=True, to="researcher.researcher"),
                ),
                (
                    "contacts",
                    models.ManyToManyField(blank=True, to="dataset.affliation"),
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
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Publications",
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
                ("citation", models.TextField(blank=True, null=True)),
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
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="File",
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
                ("name", models.TextField(blank=True, null=True)),
                (
                    "type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("dataverse", "dataverse"),
                            ("dataset", "dataset"),
                            ("file", "file"),
                        ],
                        max_length=9,
                        null=True,
                    ),
                ),
                ("url", models.URLField(blank=True, null=True, verbose_name="URL")),
                (
                    "published_at",
                    models.CharField(blank=True, max_length=25, null=True),
                ),
                ("file_type", models.CharField(blank=True, max_length=30, null=True)),
                (
                    "file_content_type",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("file_persistent_id", models.TextField(blank=True, null=True)),
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
                    "dataset",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="dataset.dataset",
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
        migrations.CreateModel(
            name="Dataverse",
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
                ("name", models.TextField(blank=True, null=True)),
                (
                    "type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("dataverse", "dataverse"),
                            ("dataset", "dataset"),
                            ("file", "file"),
                        ],
                        max_length=9,
                        null=True,
                    ),
                ),
                ("url", models.URLField(blank=True, null=True, verbose_name="URL")),
                (
                    "published_at",
                    models.CharField(blank=True, max_length=25, null=True),
                ),
                ("identifier", models.CharField(blank=True, max_length=30, null=True)),
                ("description", models.TextField(blank=True, null=True)),
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
        migrations.AddField(
            model_name="dataset",
            name="dataverse",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="dataset.dataverse",
            ),
        ),
        migrations.AddField(
            model_name="dataset",
            name="keywords",
            field=models.ManyToManyField(blank=True, to="vocabulary.keyword"),
        ),
        migrations.AddField(
            model_name="dataset",
            name="publications",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="dataset.publications",
            ),
        ),
        migrations.AddField(
            model_name="dataset",
            name="publisher",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="institution.institution",
            ),
        ),
        migrations.AddField(
            model_name="dataset",
            name="toc_sections",
            field=models.ManyToManyField(blank=True, to="issue.tocsection"),
        ),
        migrations.AddField(
            model_name="dataset",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_last_mod_user",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Updater",
            ),
        ),
    ]
