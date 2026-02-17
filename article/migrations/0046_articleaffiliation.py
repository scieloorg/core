# Generated manually for ArticleAffiliation model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0006_alter_organization_location'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('article', '0045_article_invalid_data_availability_status_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArticleAffiliation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='Last update date')),
                ('raw_text', models.TextField(blank=True, help_text='Free text, unstructured organization data', null=True, verbose_name='Raw Text')),
                ('raw_institution_name', models.CharField(blank=True, help_text='Raw institution name as provided', max_length=510, null=True, verbose_name='Raw Institution Name')),
                ('raw_country_name', models.CharField(blank=True, help_text='Raw country name as provided', max_length=255, null=True, verbose_name='Raw Country Name')),
                ('raw_country_code', models.CharField(blank=True, help_text='Raw country code (ISO) as provided', max_length=3, null=True, verbose_name='Raw Country Code')),
                ('raw_state_name', models.CharField(blank=True, help_text='Raw state name as provided', max_length=255, null=True, verbose_name='Raw State Name')),
                ('raw_state_acron', models.CharField(blank=True, help_text='Raw state acronym as provided', max_length=10, null=True, verbose_name='Raw State Acronym')),
                ('raw_city_name', models.CharField(blank=True, help_text='Raw city name as provided', max_length=255, null=True, verbose_name='Raw City Name')),
                ('article', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='affiliations', to='article.article', verbose_name='Article')),
                ('creator', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_creator', to=settings.AUTH_USER_MODEL, verbose_name='Creator')),
                ('organization', models.ForeignKey(blank=True, help_text='Structured organization reference', null=True, on_delete=django.db.models.deletion.SET_NULL, to='organization.organization', verbose_name='Organization')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_last_mod_user', to=settings.AUTH_USER_MODEL, verbose_name='Updater')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddIndex(
            model_name='articleaffiliation',
            index=models.Index(fields=['article'], name='article_art_article_idx'),
        ),
        migrations.AddIndex(
            model_name='articleaffiliation',
            index=models.Index(fields=['organization'], name='article_art_organiz_idx'),
        ),
    ]
