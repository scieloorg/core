# Generated by Django 5.0.8 on 2025-04-27 18:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("editorialboard", "0005_alter_editorialboardmember_unique_together_and_more"),
        ("researcher", "0005_newresearcher_researcherids_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="editorialboardmember",
            name="researcher",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="researcher.newresearcher",
            ),
        ),
        migrations.DeleteModel(
            name="EditorialBoard",
        ),
    ]
