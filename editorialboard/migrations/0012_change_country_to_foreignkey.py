# Generated manually to change manual_institution_country from CharField to ForeignKey

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("location", "0011_alter_city_created_alter_city_name_and_more"),
        ("editorialboard", "0011_add_manual_input_fields"),
    ]

    operations = [
        # First, remove the old CharField
        migrations.RemoveField(
            model_name="editorialboardmember",
            name="manual_institution_country",
        ),
        # Then, add the new ForeignKey field
        migrations.AddField(
            model_name="editorialboardmember",
            name="manual_institution_country",
            field=models.ForeignKey(
                blank=True,
                help_text="Select institution country from the list",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="location.country",
                verbose_name="Institution country",
            ),
        ),
    ]
