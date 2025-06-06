# Generated by Django 5.0.8 on 2025-05-26 14:22

import django.db.models.deletion
import wagtail.fields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vocabulary", "0003_keyword_html_text"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="keyword",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Data de criação"
            ),
        ),
        migrations.AlterField(
            model_name="keyword",
            name="creator",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_creator",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Criador",
            ),
        ),
        migrations.AlterField(
            model_name="keyword",
            name="html_text",
            field=wagtail.fields.RichTextField(
                blank=True, null=True, verbose_name="Texto Rico"
            ),
        ),
        migrations.AlterField(
            model_name="keyword",
            name="updated",
            field=models.DateTimeField(
                auto_now=True, verbose_name="Data da última atualização"
            ),
        ),
        migrations.AlterField(
            model_name="keyword",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_last_mod_user",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Atualizador",
            ),
        ),
        migrations.AlterField(
            model_name="keyword",
            name="vocabulary",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="vocabulary.vocabulary",
                verbose_name="Vocabulário",
            ),
        ),
        migrations.AlterField(
            model_name="vocabulary",
            name="acronym",
            field=models.CharField(
                blank=True,
                max_length=10,
                null=True,
                verbose_name="Acrônimo do vocabulário",
            ),
        ),
        migrations.AlterField(
            model_name="vocabulary",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Data de criação"
            ),
        ),
        migrations.AlterField(
            model_name="vocabulary",
            name="creator",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_creator",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Criador",
            ),
        ),
        migrations.AlterField(
            model_name="vocabulary",
            name="name",
            field=models.TextField(
                blank=True, null=True, verbose_name="Nome do vocabulário"
            ),
        ),
        migrations.AlterField(
            model_name="vocabulary",
            name="updated",
            field=models.DateTimeField(
                auto_now=True, verbose_name="Data da última atualização"
            ),
        ),
        migrations.AlterField(
            model_name="vocabulary",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_last_mod_user",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Atualizador",
            ),
        ),
    ]
