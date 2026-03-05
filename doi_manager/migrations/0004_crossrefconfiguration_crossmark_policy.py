from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("doi_manager", "0003_alter_crossrefconfiguration_created_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="crossrefconfiguration",
            name="crossmark_policy",
            field=models.URLField(
                blank=True,
                help_text="URL of the CrossMark policy page for this journal.",
                max_length=255,
                null=True,
                verbose_name="CrossMark Policy URL",
            ),
        ),
    ]
