# Generated manually for adding RawOrganizationMixin fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("journal", "0054_journaltableofcontents"),
    ]

    operations = [
        # Add RawOrganizationMixin fields to OwnerHistory
        migrations.AddField(
            model_name="ownerhistory",
            name="raw_text",
            field=models.TextField(
                blank=True,
                help_text="Free text, unstructured organization data",
                null=True,
                verbose_name="Raw Text",
            ),
        ),
        migrations.AddField(
            model_name="ownerhistory",
            name="raw_institution_name",
            field=models.CharField(
                blank=True,
                help_text="Raw institution name as provided",
                max_length=510,
                null=True,
                verbose_name="Raw Institution Name",
            ),
        ),
        migrations.AddField(
            model_name="ownerhistory",
            name="raw_country_name",
            field=models.CharField(
                blank=True,
                help_text="Raw country name as provided",
                max_length=255,
                null=True,
                verbose_name="Raw Country Name",
            ),
        ),
        migrations.AddField(
            model_name="ownerhistory",
            name="raw_country_code",
            field=models.CharField(
                blank=True,
                help_text="Raw country code (ISO) as provided",
                max_length=3,
                null=True,
                verbose_name="Raw Country Code",
            ),
        ),
        migrations.AddField(
            model_name="ownerhistory",
            name="raw_state_name",
            field=models.CharField(
                blank=True,
                help_text="Raw state name as provided",
                max_length=255,
                null=True,
                verbose_name="Raw State Name",
            ),
        ),
        migrations.AddField(
            model_name="ownerhistory",
            name="raw_state_acron",
            field=models.CharField(
                blank=True,
                help_text="Raw state acronym as provided",
                max_length=10,
                null=True,
                verbose_name="Raw State Acronym",
            ),
        ),
        migrations.AddField(
            model_name="ownerhistory",
            name="raw_city_name",
            field=models.CharField(
                blank=True,
                help_text="Raw city name as provided",
                max_length=255,
                null=True,
                verbose_name="Raw City Name",
            ),
        ),
        # Add RawOrganizationMixin fields to PublisherHistory
        migrations.AddField(
            model_name="publisherhistory",
            name="raw_text",
            field=models.TextField(
                blank=True,
                help_text="Free text, unstructured organization data",
                null=True,
                verbose_name="Raw Text",
            ),
        ),
        migrations.AddField(
            model_name="publisherhistory",
            name="raw_institution_name",
            field=models.CharField(
                blank=True,
                help_text="Raw institution name as provided",
                max_length=510,
                null=True,
                verbose_name="Raw Institution Name",
            ),
        ),
        migrations.AddField(
            model_name="publisherhistory",
            name="raw_country_name",
            field=models.CharField(
                blank=True,
                help_text="Raw country name as provided",
                max_length=255,
                null=True,
                verbose_name="Raw Country Name",
            ),
        ),
        migrations.AddField(
            model_name="publisherhistory",
            name="raw_country_code",
            field=models.CharField(
                blank=True,
                help_text="Raw country code (ISO) as provided",
                max_length=3,
                null=True,
                verbose_name="Raw Country Code",
            ),
        ),
        migrations.AddField(
            model_name="publisherhistory",
            name="raw_state_name",
            field=models.CharField(
                blank=True,
                help_text="Raw state name as provided",
                max_length=255,
                null=True,
                verbose_name="Raw State Name",
            ),
        ),
        migrations.AddField(
            model_name="publisherhistory",
            name="raw_state_acron",
            field=models.CharField(
                blank=True,
                help_text="Raw state acronym as provided",
                max_length=10,
                null=True,
                verbose_name="Raw State Acronym",
            ),
        ),
        migrations.AddField(
            model_name="publisherhistory",
            name="raw_city_name",
            field=models.CharField(
                blank=True,
                help_text="Raw city name as provided",
                max_length=255,
                null=True,
                verbose_name="Raw City Name",
            ),
        ),
        # Add RawOrganizationMixin fields to SponsorHistory
        migrations.AddField(
            model_name="sponsorhistory",
            name="raw_text",
            field=models.TextField(
                blank=True,
                help_text="Free text, unstructured organization data",
                null=True,
                verbose_name="Raw Text",
            ),
        ),
        migrations.AddField(
            model_name="sponsorhistory",
            name="raw_institution_name",
            field=models.CharField(
                blank=True,
                help_text="Raw institution name as provided",
                max_length=510,
                null=True,
                verbose_name="Raw Institution Name",
            ),
        ),
        migrations.AddField(
            model_name="sponsorhistory",
            name="raw_country_name",
            field=models.CharField(
                blank=True,
                help_text="Raw country name as provided",
                max_length=255,
                null=True,
                verbose_name="Raw Country Name",
            ),
        ),
        migrations.AddField(
            model_name="sponsorhistory",
            name="raw_country_code",
            field=models.CharField(
                blank=True,
                help_text="Raw country code (ISO) as provided",
                max_length=3,
                null=True,
                verbose_name="Raw Country Code",
            ),
        ),
        migrations.AddField(
            model_name="sponsorhistory",
            name="raw_state_name",
            field=models.CharField(
                blank=True,
                help_text="Raw state name as provided",
                max_length=255,
                null=True,
                verbose_name="Raw State Name",
            ),
        ),
        migrations.AddField(
            model_name="sponsorhistory",
            name="raw_state_acron",
            field=models.CharField(
                blank=True,
                help_text="Raw state acronym as provided",
                max_length=10,
                null=True,
                verbose_name="Raw State Acronym",
            ),
        ),
        migrations.AddField(
            model_name="sponsorhistory",
            name="raw_city_name",
            field=models.CharField(
                blank=True,
                help_text="Raw city name as provided",
                max_length=255,
                null=True,
                verbose_name="Raw City Name",
            ),
        ),
        # Add RawOrganizationMixin fields to CopyrightHolderHistory
        migrations.AddField(
            model_name="copyrightholderhistory",
            name="raw_text",
            field=models.TextField(
                blank=True,
                help_text="Free text, unstructured organization data",
                null=True,
                verbose_name="Raw Text",
            ),
        ),
        migrations.AddField(
            model_name="copyrightholderhistory",
            name="raw_institution_name",
            field=models.CharField(
                blank=True,
                help_text="Raw institution name as provided",
                max_length=510,
                null=True,
                verbose_name="Raw Institution Name",
            ),
        ),
        migrations.AddField(
            model_name="copyrightholderhistory",
            name="raw_country_name",
            field=models.CharField(
                blank=True,
                help_text="Raw country name as provided",
                max_length=255,
                null=True,
                verbose_name="Raw Country Name",
            ),
        ),
        migrations.AddField(
            model_name="copyrightholderhistory",
            name="raw_country_code",
            field=models.CharField(
                blank=True,
                help_text="Raw country code (ISO) as provided",
                max_length=3,
                null=True,
                verbose_name="Raw Country Code",
            ),
        ),
        migrations.AddField(
            model_name="copyrightholderhistory",
            name="raw_state_name",
            field=models.CharField(
                blank=True,
                help_text="Raw state name as provided",
                max_length=255,
                null=True,
                verbose_name="Raw State Name",
            ),
        ),
        migrations.AddField(
            model_name="copyrightholderhistory",
            name="raw_state_acron",
            field=models.CharField(
                blank=True,
                help_text="Raw state acronym as provided",
                max_length=10,
                null=True,
                verbose_name="Raw State Acronym",
            ),
        ),
        migrations.AddField(
            model_name="copyrightholderhistory",
            name="raw_city_name",
            field=models.CharField(
                blank=True,
                help_text="Raw city name as provided",
                max_length=255,
                null=True,
                verbose_name="Raw City Name",
            ),
        ),
    ]
