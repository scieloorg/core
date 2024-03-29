# Generated by Django 4.2.7 on 2024-01-29 00:08

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0013_alter_journal_ftp"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="officialjournal",
            name="issn_print_status",
        ),
        migrations.AddField(
            model_name="officialjournal",
            name="issn_print_is_active",
            field=models.BooleanField(
                default=False, verbose_name="ISSN Print is active"
            ),
        ),
    ]
