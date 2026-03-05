import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("article", "0047_articleaffiliation_normalized_and_more"),
        ("doi_manager", "0003_alter_crossrefconfiguration_created_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add new fields to CrossRefConfiguration
        migrations.AddField(
            model_name="crossrefconfiguration",
            name="crossmark_policy_url",
            field=models.URLField(
                blank=True,
                null=True,
                verbose_name="Crossmark Policy URL",
                help_text="URL of the journal crossmark policy page",
            ),
        ),
        migrations.AddField(
            model_name="crossrefconfiguration",
            name="crossmark_policy_doi",
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name="Crossmark Policy DOI",
                help_text="DOI of the journal crossmark policy",
            ),
        ),
        migrations.AddField(
            model_name="crossrefconfiguration",
            name="username",
            field=models.CharField(
                blank=True,
                max_length=64,
                null=True,
                verbose_name="Crossref Username",
                help_text="Username/login for Crossref deposit API",
            ),
        ),
        migrations.AddField(
            model_name="crossrefconfiguration",
            name="password",
            field=models.CharField(
                blank=True,
                max_length=64,
                null=True,
                verbose_name="Crossref Password",
                help_text="Password for Crossref deposit API",
            ),
        ),
        migrations.AddField(
            model_name="crossrefconfiguration",
            name="use_test_server",
            field=models.BooleanField(
                default=False,
                verbose_name="Use test server",
                help_text="If checked, deposits will be sent to the Crossref test server",
            ),
        ),
        # Create CrossRefDeposit model
        migrations.CreateModel(
            name="CrossRefDeposit",
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
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("submitted", "Submitted"),
                            ("success", "Success"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "submission_date",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Submission Date"
                    ),
                ),
                (
                    "response",
                    models.TextField(
                        blank=True,
                        null=True,
                        verbose_name="Response",
                        help_text="Response from Crossref API",
                    ),
                ),
                (
                    "detail",
                    models.JSONField(blank=True, null=True, verbose_name="Detail"),
                ),
                (
                    "article",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="crossref_deposits",
                        to="article.article",
                        verbose_name="Article",
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
                "verbose_name": "Crossref Deposit",
                "verbose_name_plural": "Crossref Deposits",
                "indexes": [
                    models.Index(
                        fields=["status"], name="doi_mgr_deposit_status_idx"
                    ),
                    models.Index(
                        fields=["submission_date"],
                        name="doi_mgr_deposit_subdate_idx",
                    ),
                ],
            },
        ),
    ]
