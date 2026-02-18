# Generated migration

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields


class Migration(migrations.Migration):

    dependencies = [
        ('article', '0049_contribcollab_remove_article_collab'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContribPerson',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='Last update date')),
                ('declared_name', models.CharField(blank=True, max_length=255, null=True, verbose_name='Declared Name')),
                ('given_names', models.CharField(blank=True, max_length=255, null=True, verbose_name='Given Names')),
                ('last_name', models.CharField(blank=True, max_length=255, null=True, verbose_name='Last Name')),
                ('suffix', models.CharField(blank=True, max_length=50, null=True, verbose_name='Suffix')),
                ('fullname', models.CharField(blank=True, max_length=255, null=True, verbose_name='Full Name')),
                ('orcid', models.CharField(blank=True, help_text='ORCID identifier (e.g., 0000-0002-1825-0097)', max_length=19, null=True, verbose_name='ORCID')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='Email')),
                ('affiliation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contrib_persons', to='article.articleaffiliation', verbose_name='Affiliation')),
                ('article', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='contrib_persons', to='article.article', verbose_name='Article')),
                ('creator', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_creator', to=settings.AUTH_USER_MODEL, verbose_name='Creator')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_last_mod_user', to=settings.AUTH_USER_MODEL, verbose_name='Updater')),
            ],
            options={
                'indexes': [
                    models.Index(fields=['article'], name='article_con_article_idx_cp'),
                    models.Index(fields=['affiliation'], name='article_con_affilia_idx_cp'),
                    models.Index(fields=['orcid'], name='article_con_orcid_idx_cp'),
                ],
            },
        ),
        migrations.RemoveField(
            model_name='article',
            name='researchers',
        ),
    ]
