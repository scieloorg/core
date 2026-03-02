from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('location', '0003_alter_city_options_alter_country_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='city',
            name='status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('RAW', 'RAW'),
                    ('CLEANED', 'CLEANED'),
                    ('MATCHED', 'MATCHED'),
                    ('VERIFIED', 'VERIFIED'),
                    ('REJECTED', 'REJECTED')
                ],
                default='RAW',
                max_length=10,
                null=True,
                verbose_name='Status'
            ),
        ),
        migrations.AddField(
            model_name='state',
            name='status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('RAW', 'RAW'),
                    ('CLEANED', 'CLEANED'),
                    ('MATCHED', 'MATCHED'),
                    ('VERIFIED', 'VERIFIED'),
                    ('REJECTED', 'REJECTED')
                ],
                default='RAW',
                max_length=10,
                null=True,
                verbose_name='Status'
            ),
        ),
        migrations.AddField(
            model_name='country',
            name='status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('RAW', 'RAW'),
                    ('CLEANED', 'CLEANED'),
                    ('MATCHED', 'MATCHED'),
                    ('VERIFIED', 'VERIFIED'),
                    ('REJECTED', 'REJECTED')
                ],
                default='RAW',
                max_length=10,
                null=True,
                verbose_name='Status'
            ),
        ),
    ]
