# Generated migration for crossmark update policy

import django.db.models.deletion
import modelcluster.fields
import wagtail.fields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_alter_language_options_alter_license_options_and_more"),
        ("journal", "0056_delete_journallogo"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="journal",
            name="crossmark_policy_doi",
            field=models.CharField(
                blank=True,
                help_text="DOI of the crossmark update policy page for this journal",
                max_length=100,
                null=True,
                verbose_name="Crossmark Policy DOI",
            ),
        ),
        migrations.AddField(
            model_name="journal",
            name="crossmark_doi_is_active",
            field=models.BooleanField(
                default=False,
                help_text="Indicates whether the crossmark policy DOI page is active",
                verbose_name="Crossmark DOI is active",
            ),
        ),
        migrations.CreateModel(
            name="UpdatePolicy",
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
                    "sort_order",
                    models.IntegerField(blank=True, editable=False, null=True),
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
                    "rich_text",
                    wagtail.fields.RichTextField(
                        blank=True,
                        null=True,
                        verbose_name="Rich Text",
                    ),
                ),
                (
                    "policy_type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("correction", "Correction"),
                            ("retraction", "Retraction"),
                            ("partial-retraction", "Partial Retraction"),
                            ("withdrawal", "Withdrawal"),
                            ("expression-of-concern", "Expression of Concern"),
                            ("other", "Other"),
                        ],
                        help_text="Type of update policy (e.g. correction, retraction, withdrawal)",
                        max_length=30,
                        null=True,
                        verbose_name="Policy Type",
                    ),
                ),
                (
                    "url",
                    models.URLField(
                        blank=True,
                        help_text="URL of the policy page describing how the journal handles this type of update",
                        null=True,
                        verbose_name="Policy URL",
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
                        related_name="update_policy",
                        to="journal.journal",
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
            options={
                "verbose_name": "Update Policy",
                "verbose_name_plural": "Update Policies",
                "ordering": ["sort_order"],
                "abstract": False,
            },
        ),
    ]
