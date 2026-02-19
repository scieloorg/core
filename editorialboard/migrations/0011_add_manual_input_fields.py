# Generated manually for editorial board member manual input fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("editorialboard", "0010_alter_editorialboardmember_created_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="editorialboardmember",
            name="manual_given_names",
            field=models.CharField(
                blank=True,
                help_text="Enter given names if researcher is not in the database",
                max_length=128,
                null=True,
                verbose_name="Given names",
            ),
        ),
        migrations.AddField(
            model_name="editorialboardmember",
            name="manual_last_name",
            field=models.CharField(
                blank=True,
                help_text="Enter last name if researcher is not in the database",
                max_length=64,
                null=True,
                verbose_name="Last name",
            ),
        ),
        migrations.AddField(
            model_name="editorialboardmember",
            name="manual_suffix",
            field=models.CharField(
                blank=True,
                help_text="Enter suffix (e.g., Jr., Sr., III) if applicable",
                max_length=16,
                null=True,
                verbose_name="Suffix",
            ),
        ),
        migrations.AddField(
            model_name="editorialboardmember",
            name="manual_institution_name",
            field=models.CharField(
                blank=True,
                help_text="Enter institution name if not in the database",
                max_length=255,
                null=True,
                verbose_name="Institution name",
            ),
        ),
        migrations.AddField(
            model_name="editorialboardmember",
            name="manual_institution_acronym",
            field=models.CharField(
                blank=True,
                help_text="Enter institution acronym if applicable",
                max_length=64,
                null=True,
                verbose_name="Institution acronym",
            ),
        ),
        migrations.AddField(
            model_name="editorialboardmember",
            name="manual_institution_city",
            field=models.CharField(
                blank=True,
                help_text="Enter institution city",
                max_length=128,
                null=True,
                verbose_name="Institution city",
            ),
        ),
        migrations.AddField(
            model_name="editorialboardmember",
            name="manual_institution_state",
            field=models.CharField(
                blank=True,
                help_text="Enter institution state/province",
                max_length=128,
                null=True,
                verbose_name="Institution state",
            ),
        ),
        migrations.AddField(
            model_name="editorialboardmember",
            name="manual_institution_country",
            field=models.CharField(
                blank=True,
                help_text="Enter institution country",
                max_length=128,
                null=True,
                verbose_name="Institution country",
            ),
        ),
        migrations.AddField(
            model_name="editorialboardmember",
            name="manual_orcid",
            field=models.CharField(
                blank=True,
                help_text="Enter ORCID identifier (e.g., 0000-0000-0000-0000)",
                max_length=64,
                null=True,
                verbose_name="ORCID",
            ),
        ),
        migrations.AddField(
            model_name="editorialboardmember",
            name="manual_lattes",
            field=models.CharField(
                blank=True,
                help_text="Enter Lattes CV identifier",
                max_length=64,
                null=True,
                verbose_name="Lattes CV",
            ),
        ),
        migrations.AddField(
            model_name="editorialboardmember",
            name="manual_email",
            field=models.EmailField(
                blank=True,
                help_text="Enter email address",
                max_length=254,
                null=True,
                verbose_name="Email",
            ),
        ),
    ]
