# Generated by Django 5.0.3 on 2024-05-28 18:09

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("article", "0012_alter_article_publisher"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="article_license",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
