# Generated by Django 4.1.10 on 2023-08-21 18:54

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("institution", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="institution",
            index=models.Index(fields=["name"], name="institution_name_955317_idx"),
        ),
        migrations.AddIndex(
            model_name="institution",
            index=models.Index(
                fields=["institution_type"], name="institution_institu_598c48_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="institution",
            index=models.Index(
                fields=["acronym"], name="institution_acronym_bacdf0_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="institution",
            index=models.Index(
                fields=["level_1"], name="institution_level_1_4833b5_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="institution",
            index=models.Index(
                fields=["level_2"], name="institution_level_2_425cb0_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="institution",
            index=models.Index(
                fields=["level_3"], name="institution_level_3_f7c7ce_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="institution",
            index=models.Index(fields=["url"], name="institution_url_8f7c3c_idx"),
        ),
    ]
