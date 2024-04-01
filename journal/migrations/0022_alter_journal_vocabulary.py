# Generated by Django 5.0.3 on 2024-03-28 17:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0021_journallicense_journal_journal_use_license_and_more"),
        ("vocabulary", "0003_keyword_html_text"),
    ]

    operations = [
        migrations.AlterField(
            model_name="journal",
            name="vocabulary",
            field=models.ForeignKey(
                blank=True,
                help_text="As palavras-chave devem ser extraídas de thesaurus,dicionários temáticos ou listas controladas nos idiomas que o periódico pública.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="vocabulary.vocabulary",
            ),
        ),
    ]
