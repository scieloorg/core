# Generated manually for NormAffiliation model and ArticleAffiliation updates

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('location', '0013_alter_city_options_alter_country_options_and_more'),
        ('organization', '0006_alter_organization_location'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('article', '0046_articleaffiliation'),
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
            index=models.Index(fields=['organization'], name='article_nor_organiz_idx'),
        ),
        migrations.AddIndex(
            model_name='normaffiliation',
            index=models.Index(fields=['location'], name='article_nor_locatio_idx'),
        ),
        # Add unique_together constraint for NormAffiliation
        migrations.AlterUniqueTogether(
            name='normaffiliation',
            unique_together={('organization', 'location', 'level_1', 'level_2', 'level_3')},
        ),
        # Add raw_level fields to ArticleAffiliation
        migrations.AddField(
            model_name='articleaffiliation',
            name='raw_level_1',
            field=models.CharField(blank=True, help_text='Raw first level of organization division', max_length=255, null=True, verbose_name='Raw Level 1'),
        ),
        migrations.AddField(
            model_name='articleaffiliation',
            name='raw_level_2',
            field=models.CharField(blank=True, help_text='Raw second level of organization division', max_length=255, null=True, verbose_name='Raw Level 2'),
        ),
        migrations.AddField(
            model_name='articleaffiliation',
            name='raw_level_3',
            field=models.CharField(blank=True, help_text='Raw third level of organization division', max_length=255, null=True, verbose_name='Raw Level 3'),
        ),
        # Add normalized FK field to ArticleAffiliation
        migrations.AddField(
            model_name='articleaffiliation',
            name='normalized',
            field=models.ForeignKey(blank=True, help_text='Reference to normalized affiliation data', null=True, on_delete=django.db.models.deletion.SET_NULL, to='article.normaffiliation', verbose_name='Normalized Affiliation'),
        ),
        # Add index for normalized field in ArticleAffiliation
        migrations.AddIndex(
            model_name='articleaffiliation',
            index=models.Index(fields=['normalized'], name='article_art_normaliz_idx'),
        ),
    ]
