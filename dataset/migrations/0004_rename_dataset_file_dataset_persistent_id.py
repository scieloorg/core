# Generated by Django 4.1.8 on 2023-07-30 23:47

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("dataset", "0003_rename_dataverse_dataset_identifier_of_dataverse_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="file",
            old_name="dataset",
            new_name="dataset_persistent_id",
        ),
    ]
