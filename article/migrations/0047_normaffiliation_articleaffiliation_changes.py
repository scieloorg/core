# Generated manually for ArticleAffiliation updates to reference NormAffiliation

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0012_normaffiliation'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('article', '0046_articleaffiliation'),
    ]

    operations = [
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
        # Add normalized FK field to ArticleAffiliation - references organization.NormAffiliation
        migrations.AddField(
            model_name='articleaffiliation',
            name='normalized',
            field=models.ForeignKey(blank=True, help_text='Reference to normalized affiliation data', null=True, on_delete=django.db.models.deletion.SET_NULL, to='organization.normaffiliation', verbose_name='Normalized Affiliation'),
        ),
        # Add index for normalized field in ArticleAffiliation
        migrations.AddIndex(
            model_name='articleaffiliation',
            index=models.Index(fields=['normalized'], name='article_art_normaliz_idx'),
        ),
    ]
