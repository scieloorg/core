# Generated by Django 5.0.8 on 2025-07-18 04:00

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("journal", "0039_journalproxyeditor"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddIndex(
            model_name="subject",
            index=models.Index(fields=["value"], name="journal_sub_value_0138a4_idx"),
        ),
        migrations.AddIndex(
            model_name="subject",
            index=models.Index(fields=["code"], name="journal_sub_code_2d8324_idx"),
        ),
        migrations.AddIndex(
            model_name="subjectdescriptor",
            index=models.Index(fields=["value"], name="journal_sub_value_e05034_idx"),
        ),
    ]
