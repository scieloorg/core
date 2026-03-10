from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("doi_manager", "0003_alter_crossrefconfiguration_created_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="crossrefconfiguration",
            name="password",
            field=models.CharField(
                blank=True,
                help_text="Password for authenticating with the CrossRef deposit API.",
                max_length=64,
                null=True,
                verbose_name="Password",
            ),
        ),
    ]
