# Generated by Django 5.0.3 on 2024-04-19 17:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("journal", "0022_alter_journal_vocabulary"),
    ]

    operations = [
        migrations.AlterField(
            model_name="officialjournal",
            name="issn_electronic",
            field=models.CharField(
                blank=True, max_length=9, null=True, verbose_name="ISSN Electronic"
            ),
        ),
    ]
