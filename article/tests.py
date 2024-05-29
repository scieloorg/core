from django.test import TestCase
from django_test_migrations.migrator import Migrator

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