# Generated by Django 4.1.8 on 2023-07-24 16:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0007_journal_and_more"),
        ("issue", "0008_remove_bibliographicstrip_subtitle_and_more"),
    ]

    operations = [
        migrations.AlterField(
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
    ]