# Generated by Django 5.0.8 on 2025-04-15 17:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("journal", "0030_alter_journal_options"),
        ("organization", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="copyrightholderhistory",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="organization.organization",
            ),
        ),
        migrations.AddField(
            model_name="ownerhistory",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="organization.organization",
            ),
        ),
        migrations.AddField(
            model_name="publisherhistory",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="organization.organization",
            ),
        ),
        migrations.AddField(
            model_name="sponsorhistory",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="organization.organization",
            ),
        ),
    ]
