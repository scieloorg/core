from freezegun import freeze_time
from django.test import TestCase
from django_test_migrations.migrator import Migrator
from datetime import datetime
from django.utils.timezone import make_aware

from article.models import Article
from article.tasks import remove_duplicate_articles


class TestArticleMigration(TestCase):
    def test_migration_0013_article_article_license(self):
        migrator = Migrator(database='default')
        old_state = migrator.apply_initial_migration(('article', '0012_alter_article_publisher'))
        Article = old_state.apps.get_model('article', 'Article')
        LicenseStatement = old_state.apps.get_model('core', 'LicenseStatement')
        article = Article.objects.create()
        license_statement = LicenseStatement.objects.create(url="https://www.teste.com.br")
        article.license_statements.add(license_statement)

        new_state = migrator.apply_tested_migration(('article', '0013_article_article_license'))

        Article = new_state.apps.get_model('article', 'Article')

        article = Article.objects.first()
        self.assertEqual(article.article_license, 'https://www.teste.com.br')
        migrator.reset()


class RemoveDuplicateArticlesTest(TestCase):
    def create_article_at_time(self, dt, v3):
        @freeze_time(dt)
        def create_article():
            Article.objects.create(pid_v3=v3, created=make_aware(datetime.strptime(dt, "%Y-%m-%d")))
        create_article()

    def test_remove_duplicates_keeps_earliest_article(self):
        self.create_article_at_time("2023-01-01", "pid1")
        self.create_article_at_time("2023-01-02", "pid1")
        self.create_article_at_time("2023-01-03", "pid1")
        remove_duplicate_articles()
        self.assertEqual(Article.objects.all().count(), 1)
        self.assertEqual(Article.objects.all()[0].created, make_aware(datetime(2023, 1, 1)))

    def test_no_removal_if_only_one_article(self):
        self.create_article_at_time("2023-01-01", "pid1")
        remove_duplicate_articles()
        self.assertEqual(Article.objects.all().count(), 1)
        self.assertEqual(Article.objects.all()[0].created, make_aware(datetime(2023, 1, 1)))

    def test_remove_duplicates_for_multiple_pids(self):
        self.create_article_at_time("2022-06-03", "pid2")
        self.create_article_at_time("2022-06-04", "pid2")
        self.create_article_at_time("2022-07-08", "pid3")
        self.create_article_at_time("2022-06-14", "pid3")
        remove_duplicate_articles()
        self.assertEqual(Article.objects.filter(pid_v3="pid2").count(), 1)
        self.assertEqual(Article.objects.filter(pid_v3="pid3").count(), 1)
        self.assertEqual(Article.objects.get(pid_v3="pid2").created, make_aware(datetime(2022, 6, 3)))
        self.assertEqual(Article.objects.get(pid_v3="pid3").created, make_aware(datetime(2022, 6, 14)))
