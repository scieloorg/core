# Generated by Django 4.2.7 on 2024-01-18 22:15

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "article",
            "0006_alter_article_article_type_alter_article_first_page_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="valid",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
