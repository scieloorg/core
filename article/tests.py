from django.test import TestCase
from django.apps import apps
from django.db import connection, migrations


class TestMigration(TestCase):

    migrate_from = ('article', '0012_alter_article_publisher')
    migrate_to = ('article', '0013_article_article_license')  

    def setUp(self):
        self.migrate_to_state(self.migrate_from)

        Article = apps.get_model('article', 'Article')
        License = apps.get_model('article', 'License')
        LicenseStatement = apps.get_model('article', 'LicenseStatement')

        self.license1 = License.objects.create(license_type='by-nc')
        self.license2 = License.objects.create(license_type='by')
        self.license_statement1 = LicenseStatement.objects.create(url='https://creativecommons.org/licenses/by/4.0/')
        self.license_statement2 = LicenseStatement.objects.create(url='http://creativecommons.org/licenses/nc/4.0/')
        self.license_statement3 = LicenseStatement.objects.create(url='http://creativecommons.org/licenses/by-nc/4.0/')

        self.article1 = Article.objects.create(license=self.license)
        self.article1.license_statements.add(self.license_statement1)

        self.article2 = Article.objects.create(license=self.license)
        self.article2.license_statements.add(self.license_statement2)

        self.article3 = Article.objects.create(license=None)
        self.article3.license_statements.add(self.license1)

    def migrate_to_state(self, state):
        with connection.schema_editor() as schema_editor:
            migrate_apps = migrations.state.ProjectState.from_apps(apps)
            migration = self.get_migration(state)
            migration.apply(state=migrate_apps, schema_editor=schema_editor)

    def get_migration(self, state):
        for migration in migrations.loader.MigrationLoader(connection).graph.leaf_nodes():
            if migration[0] == state[0] and migration[1] == state[1]:
                return migrations.loader.MigrationLoader(connection).get_migration(migration)

    def test_migration(self):
        self.migrate_to_state(self.migrate_to)

        Article = apps.get_model('article', 'Article')

        article1 = Article.objects.get(id=self.article1.id)
        self.assertEqual(article1.article_license, 'https://creativecommons.org/licenses/by/4.0/')

        article2 = Article.objects.get(id=self.article2.id)
        self.assertEqual(article2.article_license, 'http://creativecommons.org/licenses/nc/4.0/')

        article3 = Article.objects.get(id=self.article3.id)
        self.assertEqual(article3.article_license, 'by-nc')

