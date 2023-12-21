# Generated by Django 4.2.7 on 2023-12-19 17:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("issue", "0001_initial"),
        ("location", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("journal", "0001_initial"),
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="city",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="location.city",
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="creator",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_creator",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Creator",
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="journal",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="journal.journal",
                verbose_name="Journal",
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="license",
            field=models.ManyToManyField(blank=True, to="core.license"),
        ),
        migrations.AddField(
            model_name="issue",
            name="sections",
            field=models.ManyToManyField(blank=True, to="issue.tocsection"),
        ),
        migrations.AddField(
            model_name="issue",
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
        migrations.AddField(
            model_name="bibliographicstrip",
            name="creator",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_creator",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Creator",
            ),
        ),
        migrations.AddField(
            model_name="bibliographicstrip",
            name="issue",
            field=modelcluster.fields.ParentalKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="bibliographic_strip",
                to="issue.issue",
            ),
        ),
        migrations.AddField(
            model_name="bibliographicstrip",
            name="language",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="core.language",
                verbose_name="Idioma",
            ),
        ),
        migrations.AddField(
            model_name="bibliographicstrip",
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
        migrations.AddIndex(
            model_name="tocsection",
            index=models.Index(
                fields=["plain_text"], name="issue_tocse_plain_t_7515e1_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="issue",
            index=models.Index(fields=["number"], name="issue_issue_number_780a64_idx"),
        ),
        migrations.AddIndex(
            model_name="issue",
            index=models.Index(fields=["volume"], name="issue_issue_volume_71bce1_idx"),
        ),
        migrations.AddIndex(
            model_name="issue",
            index=models.Index(fields=["year"], name="issue_issue_year_7b3c42_idx"),
        ),
        migrations.AddIndex(
            model_name="issue",
            index=models.Index(fields=["month"], name="issue_issue_month_a53df7_idx"),
        ),
        migrations.AddIndex(
            model_name="issue",
            index=models.Index(
                fields=["supplement"], name="issue_issue_supplem_bd88be_idx"
            ),
        ),
    ]
