import django.contrib.postgres.fields
from django.db import migrations, models

import collection.models


class Migration(migrations.Migration):

    dependencies = [
        ("collection", "0008_collection_network_classification"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Converte o valor único existente em lista, preservando os dados
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE collection_collection
                        ALTER COLUMN network_classification TYPE varchar(20)[]
                        USING CASE
                            WHEN network_classification IS NULL
                                OR network_classification = '' THEN NULL
                            ELSE ARRAY[network_classification]
                        END;
                    """,
                    reverse_sql="""
                        ALTER TABLE collection_collection
                        ALTER COLUMN network_classification TYPE varchar(20)
                        USING network_classification[1];
                    """,
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="collection",
                    name="network_classification",
                    field=collection.models.ChoiceArrayField(
                        base_field=models.CharField(
                            choices=[
                                ("scielonetwork", "SciELO Network"),
                                ("thematic", "Thematic"),
                                ("independent", "Independent"),
                            ],
                            max_length=20,
                        ),
                        blank=True,
                        null=True,
                        size=None,
                        verbose_name="Network classification",
                    ),
                ),
            ],
        ),
    ]
