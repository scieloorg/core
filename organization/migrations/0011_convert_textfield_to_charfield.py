# Generated manually for TextField to CharField conversion

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0010_alter_organization_acronym_and_more"),
    ]

    operations = [
        # Organization model fields (from OrganizationNameMixin)
        migrations.AlterField(
            model_name="organization",
            name="name",
            field=models.CharField(max_length=255, verbose_name="Name"),
        ),
        migrations.AlterField(
            model_name="organization",
            name="acronym",
            field=models.CharField(
                blank=True, max_length=20, null=True, verbose_name="Institution Acronym"
            ),
        ),
        # OrganizationInstitutionType model
        migrations.AlterField(
            model_name="organizationinstitutiontype",
            name="name",
            field=models.CharField(
                blank=True, max_length=100, null=True, unique=True, verbose_name="Institution Type"
            ),
        ),
        # OrgLevel History models (dynamically created from BaseOrgLevel)
        migrations.AlterField(
            model_name="orglevelcopyrightholderhistory",
            name="level_1",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Organization Level 1"
            ),
        ),
        migrations.AlterField(
            model_name="orglevelcopyrightholderhistory",
            name="level_2",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Organization Level 2"
            ),
        ),
        migrations.AlterField(
            model_name="orglevelcopyrightholderhistory",
            name="level_3",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Organization Level 3"
            ),
        ),
        migrations.AlterField(
            model_name="orglevelownerhistory",
            name="level_1",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Organization Level 1"
            ),
        ),
        migrations.AlterField(
            model_name="orglevelownerhistory",
            name="level_2",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Organization Level 2"
            ),
        ),
        migrations.AlterField(
            model_name="orglevelownerhistory",
            name="level_3",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Organization Level 3"
            ),
        ),
        migrations.AlterField(
            model_name="orglevelpublisherhistory",
            name="level_1",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Organization Level 1"
            ),
        ),
        migrations.AlterField(
            model_name="orglevelpublisherhistory",
            name="level_2",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Organization Level 2"
            ),
        ),
        migrations.AlterField(
            model_name="orglevelpublisherhistory",
            name="level_3",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Organization Level 3"
            ),
        ),
        migrations.AlterField(
            model_name="orglevelsponsorhistory",
            name="level_1",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Organization Level 1"
            ),
        ),
        migrations.AlterField(
            model_name="orglevelsponsorhistory",
            name="level_2",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Organization Level 2"
            ),
        ),
        migrations.AlterField(
            model_name="orglevelsponsorhistory",
            name="level_3",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Organization Level 3"
            ),
        ),
    ]
