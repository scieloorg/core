# Generated by Django 4.1.10 on 2023-08-21 18:54

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("thematic_areas", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="genericthematicarea",
            index=models.Index(fields=["text"], name="thematic_ar_text_6dca47_idx"),
        ),
        migrations.AddIndex(
            model_name="genericthematicarea",
            index=models.Index(fields=["origin"], name="thematic_ar_origin_b71fb9_idx"),
        ),
        migrations.AddIndex(
            model_name="genericthematicarea",
            index=models.Index(fields=["level"], name="thematic_ar_level_5cd38d_idx"),
        ),
        migrations.AddIndex(
            model_name="thematicarea",
            index=models.Index(fields=["level0"], name="thematic_ar_level0_c26277_idx"),
        ),
        migrations.AddIndex(
            model_name="thematicarea",
            index=models.Index(fields=["level1"], name="thematic_ar_level1_ba9b9c_idx"),
        ),
        migrations.AddIndex(
            model_name="thematicarea",
            index=models.Index(fields=["level2"], name="thematic_ar_level2_a20cfc_idx"),
        ),
    ]
