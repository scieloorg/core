# Generated manually for refactoring BaseResearcher into ResearchNameMixin and GenderMixin

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("researcher", "0009_alter_affiliation_created_alter_affiliation_creator_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="personname",
            name="fullname",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Full Name"
            ),
        ),
        migrations.AlterField(
            model_name="newresearcher",
            name="fullname",
            field=models.CharField(
                blank=False, max_length=255, null=True, verbose_name="Full Name"
            ),
        ),
        migrations.AlterField(
            model_name="newresearcher",
            name="gender_identification_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("machine_assigned", "Machine Assigned"),
                    ("human_assigned", "Human Assigned"),
                    ("self_assigned", "Self Assigned"),
                ],
                max_length=255,
                null=True,
                verbose_name="Gender identification status",
            ),
        ),
        migrations.AddField(
            model_name="newresearcher",
            name="declared_name",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Declared Name"
            ),
        ),
        migrations.AlterField(
            model_name="institutionalauthor",
            name="collab",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Collab"
            ),
        ),
    ]
