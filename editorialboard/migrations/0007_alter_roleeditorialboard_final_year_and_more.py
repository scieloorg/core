# Generated by Django 5.0.8 on 2025-04-27 18:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("editorialboard", "0006_alter_editorialboardmember_researcher_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="roleeditorialboard",
            name="final_year",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="roleeditorialboard",
            name="initial_year",
            field=models.DateField(blank=True, null=True),
        ),
    ]
