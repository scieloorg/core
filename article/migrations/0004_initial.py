# Generated by Django 4.2.6 on 2023-11-21 01:36

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("journal", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0001_initial"),
        ("researcher", "0001_initial"),
        ("institution", "0001_initial"),
        ("article", "0003_initial"),
        ("vocabulary", "0001_initial"),
        ("issue", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
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
            model_name="article",
            name="keywords",
            field=models.ManyToManyField(blank=True, to="vocabulary.keyword"),
        ),
        migrations.AddField(
            model_name="article",
            name="languages",
            field=models.ManyToManyField(blank=True, to="core.language"),
        ),
        migrations.AddField(
            model_name="article",
            name="license",
            field=models.ManyToManyField(blank=True, to="core.license"),
        ),
        migrations.AddField(
            model_name="article",
            name="publisher",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="institution.institution",
                verbose_name="Publisher",
            ),
        ),
        migrations.AddField(
            model_name="article",
            name="researchers",
            field=models.ManyToManyField(blank=True, to="researcher.researcher"),
        ),
        migrations.AddField(
            model_name="article",
            name="titles",
            field=models.ManyToManyField(blank=True, to="article.documenttitle"),
        ),
        migrations.AddField(
            model_name="article",
            name="toc_sections",
            field=models.ManyToManyField(blank=True, to="issue.tocsection"),
        ),
        migrations.AddField(
            model_name="article",
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
            model_name="articlehistory",
            index=models.Index(
                fields=["event_type"], name="article_art_event_t_842e00_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="articlehistory",
            index=models.Index(fields=["date"], name="article_art_date_id_a35899_idx"),
        ),
        migrations.AddIndex(
            model_name="articlefunding",
            index=models.Index(
                fields=["award_id"], name="article_art_award_i_c81815_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="articlefunding",
            index=models.Index(
                fields=["funding_source"], name="article_art_funding_180f9e_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="articleeventtype",
            index=models.Index(fields=["code"], name="article_art_code_7447f4_idx"),
        ),
        migrations.AddIndex(
            model_name="articlecounttype",
            index=models.Index(fields=["code"], name="article_art_code_06822a_idx"),
        ),
        migrations.AddIndex(
            model_name="articlecount",
            index=models.Index(
                fields=["count_type"], name="article_art_count_t_ab6053_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="articlecount",
            index=models.Index(
                fields=["language"], name="article_art_languag_1293e9_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="article",
            index=models.Index(fields=["pid_v2"], name="article_art_pid_v2_fa7897_idx"),
        ),
        migrations.AddIndex(
            model_name="article",
            index=models.Index(fields=["pid_v3"], name="article_art_pid_v3_2370cc_idx"),
        ),
        migrations.AddIndex(
            model_name="article",
            index=models.Index(
                fields=["pub_date_year"], name="article_art_pub_dat_9c64b4_idx"
            ),
        ),
    ]
