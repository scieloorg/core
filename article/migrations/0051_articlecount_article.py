import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("article", "0050_remove_articlesource_am_article_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="articlecount",
            name="article",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="counts",
                to="article.article",
            ),
        ),
        migrations.AddIndex(
            model_name="articlecount",
            index=models.Index(
                fields=["article"], name="article_art_article_8968b6_idx"
            ),
        ),
        migrations.AlterUniqueTogether(
            name="articlecount",
            unique_together={("article", "count_type", "language")},
        ),
        migrations.RemoveField(
            model_name="articlecount",
            name="created",
        ),
        migrations.RemoveField(
            model_name="articlecount",
            name="updated",
        ),
        migrations.RemoveField(
            model_name="articlecount",
            name="creator",
        ),
        migrations.RemoveField(
            model_name="articlecount",
            name="updated_by",
        ),
        migrations.RemoveField(
            model_name="articlecounttype",
            name="created",
        ),
        migrations.RemoveField(
            model_name="articlecounttype",
            name="creator",
        ),
        migrations.RemoveField(
            model_name="articlecounttype",
            name="updated",
        ),
        migrations.RemoveField(
            model_name="articlecounttype",
            name="updated_by",
        ),
        migrations.AlterField(
            model_name="articlecounttype",
            name="code",
            field=models.CharField(
                blank=True,
                max_length=20,
                null=True,
                unique=True,
                verbose_name="Code",
            ),
        ),
    ]
