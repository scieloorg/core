# Generated manually to add composite index for ArticleAffiliation

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('article', '0047_normaffiliation_articleaffiliation_changes'),
    ]

    operations = [
        # Add composite index for (article, organization) in ArticleAffiliation
        migrations.AddIndex(
            model_name='articleaffiliation',
            index=models.Index(fields=['article', 'organization'], name='article_art_article_org_idx'),
        ),
    ]
