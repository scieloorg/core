# Generated by Django 3.2.12 on 2023-02-02 13:48

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("location", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Institution",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Creation date"
                    ),
                ),
                (
                    "updated",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Last update date"
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        blank=True, max_length=255, null=True, verbose_name="Nome"
                    ),
                ),
                (
                    "institution_type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("", ""),
                            (
                                "agência de apoio à pesquisa",
                                "agência de apoio à pesquisa",
                            ),
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
                        max_length=255,
                        null=True,
                        verbose_name="Institution Type",
                    ),
                ),
                (
                    "acronym",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        verbose_name="Institution Acronym",
                    ),
                ),
                (
                    "level_1",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        verbose_name="Organization Level 1",
                    ),
                ),
                (
                    "level_2",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        verbose_name="Organization Level 2",
                    ),
                ),
                (
                    "level_3",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        verbose_name="Organization Level 3",
                    ),
                ),
                ("url", models.URLField(blank=True, null=True, verbose_name="url")),
                (
                    "logo",
                    models.ImageField(
                        blank=True, null=True, upload_to="", verbose_name="Logo"
                    ),
                ),
                (
                    "is_official",
                    models.CharField(
                        blank=True,
                        choices=[("yes", "yes"), ("no", "no"), ("unknow", "unknow")],
                        max_length=6,
                        null=True,
                        verbose_name="Is official",
                    ),
                ),
                (
                    "creator",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="institution_creator",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Creator",
                    ),
                ),
                (
                    "location",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="location.location",
                    ),
                ),
                (
                    "official",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="institution.institution",
                        verbose_name="Institution",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="institution_last_mod_user",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Updater",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Sponsor",
            fields=[
                (
                    "institution_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="institution.institution",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("institution.institution",),
        ),
        migrations.CreateModel(
            name="InstitutionHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "initial_date",
                    models.DateField(
                        blank=True, null=True, verbose_name="Initial Date"
                    ),
                ),
                (
                    "final_date",
                    models.DateField(blank=True, null=True, verbose_name="Final Date"),
                ),
                (
                    "institution",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="institution.institution",
                    ),
                ),
            ],
        ),
    ]
