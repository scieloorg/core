# Generated by Django 4.2.7 on 2024-01-04 12:27

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_alter_licensestatement_unique_together"),
        ("vocabulary", "0001_initial"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="keyword",
            unique_together={("vocabulary", "language", "text")},
        ),
        migrations.AlterUniqueTogether(
            name="vocabulary",
            unique_together={("acronym", "name")},
        ),
    ]
