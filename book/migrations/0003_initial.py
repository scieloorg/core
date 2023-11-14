# Generated by Django 4.2.6 on 2023-11-13 13:53

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("book", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("researcher", "0001_initial"),
        ("location", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="location",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="location.location",
                verbose_name="Localization",
            ),
        ),
        migrations.AddField(
            model_name="book",
            name="researchers",
            field=models.ManyToManyField(
                blank=True, to="researcher.researcher", verbose_name="Authors"
            ),
        ),
        migrations.AddField(
            model_name="book",
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
            model_name="chapter",
            index=models.Index(fields=["title"], name="book_chapte_title_5891b0_idx"),
        ),
        migrations.AddIndex(
            model_name="chapter",
            index=models.Index(
                fields=["language"], name="book_chapte_languag_3589ab_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="chapter",
            index=models.Index(
                fields=["publication_date"], name="book_chapte_publica_262182_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="chapter",
            index=models.Index(fields=["book"], name="book_chapte_book_id_1b9202_idx"),
        ),
        migrations.AddIndex(
            model_name="book",
            index=models.Index(fields=["isbn"], name="book_book_isbn_6f139e_idx"),
        ),
        migrations.AddIndex(
            model_name="book",
            index=models.Index(fields=["title"], name="book_book_title_b5b75a_idx"),
        ),
        migrations.AddIndex(
            model_name="book",
            index=models.Index(
                fields=["synopsis"], name="book_book_synopsi_3faa60_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="book",
            index=models.Index(fields=["doi"], name="book_book_doi_3c6aea_idx"),
        ),
        migrations.AddIndex(
            model_name="book",
            index=models.Index(fields=["eisbn"], name="book_book_eisbn_019598_idx"),
        ),
        migrations.AddIndex(
            model_name="book",
            index=models.Index(fields=["year"], name="book_book_year_62fef9_idx"),
        ),
        migrations.AddIndex(
            model_name="book",
            index=models.Index(
                fields=["identifier"], name="book_book_identif_c4b36a_idx"
            ),
        ),
    ]
