# Generated migration

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields


class Migration(migrations.Migration):

    dependencies = [
        ('article', '0048_add_composite_index_article_organization'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContribCollab',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='Last update date')),
                ('collab', models.CharField(blank=True, help_text='Name of the research group, consortium, or collaborative initiative', max_length=255, null=True, verbose_name='Collaboration')),
                ('affiliation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contrib_collabs', to='article.articleaffiliation', verbose_name='Affiliation')),
                ('article', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='contrib_collabs', to='article.article', verbose_name='Article')),
                ('creator', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_creator', to=settings.AUTH_USER_MODEL, verbose_name='Creator')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_last_mod_user', to=settings.AUTH_USER_MODEL, verbose_name='Updater')),
            ],
            options={
                'indexes': [
                    models.Index(fields=['article'], name='article_con_article_2c4b25_idx'),
                    models.Index(fields=['affiliation'], name='article_con_affilia_8f5ed8_idx'),
                ],
            },
        ),
        migrations.RemoveField(
            model_name='article',
            name='collab',
        ),
    ]
