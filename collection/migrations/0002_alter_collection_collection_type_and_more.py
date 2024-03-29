# Generated by Django 4.2.7 on 2024-01-31 13:34

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("collection", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="collection",
            name="collection_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("journals", "Journals"),
                    ("preprints", "Preprints"),
                    ("repositories", "Repositories"),
                    ("books", "Books"),
                    ("data", "Data repository"),
                ],
                max_length=20,
                null=True,
                verbose_name="Collection Type",
            ),
        ),
        migrations.AlterField(
            model_name="collection",
            name="status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("certified", "Certified"),
                    ("development", "Development"),
                    ("diffusion", "Diffusion"),
                    ("independent", "Independent"),
                ],
                max_length=20,
                null=True,
                verbose_name="Status",
            ),
        ),
    ]
