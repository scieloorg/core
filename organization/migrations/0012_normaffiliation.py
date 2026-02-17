# Generated manually for NormAffiliation model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('location', '0013_alter_city_options_alter_country_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('organization', '0011_convert_textfield_to_charfield'),
    ]

    operations = [
        # Create NormAffiliation model
        migrations.CreateModel(
            name='NormAffiliation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='Last update date')),
                ('level_1', models.CharField(blank=True, help_text='First level of organization division', max_length=255, null=True, verbose_name='Level 1')),
                ('level_2', models.CharField(blank=True, help_text='Second level of organization division', max_length=255, null=True, verbose_name='Level 2')),
                ('level_3', models.CharField(blank=True, help_text='Third level of organization division', max_length=255, null=True, verbose_name='Level 3')),
                ('creator', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_creator', to=settings.AUTH_USER_MODEL, verbose_name='Creator')),
                ('location', models.ForeignKey(blank=True, help_text='Standardized location reference', null=True, on_delete=django.db.models.deletion.SET_NULL, to='location.location', verbose_name='Location')),
                ('organization', models.ForeignKey(blank=True, help_text='Standardized organization reference', null=True, on_delete=django.db.models.deletion.SET_NULL, to='organization.organization', verbose_name='Organization')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_last_mod_user', to=settings.AUTH_USER_MODEL, verbose_name='Updater')),
            ],
            options={
                'abstract': False,
            },
        ),
        # Add indexes for NormAffiliation
        migrations.AddIndex(
            model_name='normaffiliation',
            index=models.Index(fields=['organization'], name='organizatio_organiz_idx'),
        ),
        migrations.AddIndex(
            model_name='normaffiliation',
            index=models.Index(fields=['location'], name='organizatio_locatio_idx'),
        ),
        # Add unique_together constraint for NormAffiliation
        migrations.AlterUniqueTogether(
            name='normaffiliation',
            unique_together={('organization', 'location', 'level_1', 'level_2', 'level_3')},
        ),
    ]
