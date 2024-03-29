# Generated by Django 4.2.7 on 2024-03-15 01:08

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("institution", "0004_institutiontype"),
    ]

    operations = [
        migrations.AddField(
            model_name="institution",
            name="institution_type_scielo",
            field=models.ManyToManyField(
                blank=True,
                to="institution.institutiontype",
                verbose_name="Institution Type (SciELO)",
            ),
        ),
        migrations.AlterField(
            model_name="institution",
            name="institution_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", ""),
                    ("agência de apoio à pesquisa", "agência de apoio à pesquisa"),
                    (
                        "universidade e instâncias ligadas à universidades",
                        "universidade e instâncias ligadas à universidades",
                    ),
                    (
                        "empresa ou instituto ligadas ao governo",
                        "empresa ou instituto ligadas ao governo",
                    ),
                    ("organização privada", "organização privada"),
                    (
                        "organização sem fins de lucros",
                        "organização sem fins de lucros",
                    ),
                    (
                        "sociedade científica, associação pós-graduação, associação profissional",
                        "sociedade científica, associação pós-graduação, associação profissional",
                    ),
                    ("outros", "outros"),
                ],
                max_length=100,
                null=True,
                verbose_name="Institution Type (MEC)",
            ),
        ),
    ]
