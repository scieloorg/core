from freezegun import freeze_time
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django_test_migrations.migrator import Migrator
from datetime import datetime
from django.utils.timezone import make_aware

from article.models import Article, ArticleFormat
from article.tasks import remove_duplicate_articles
from core.users.models import User


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


class ArticleFormatModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            name="admin",
        )
        self.article = Article.objects.create(
            pid_v3="P3swRmPHQfy37r9xRbLCw8G",
            sps_pkg_name="0001-3714-rm-30-04-299",
        )

        self.test_file = SimpleUploadedFile("test_file.xml", b"<root><element>Test</element></root>", content_type="application/xml")
        self.test_file2 = SimpleUploadedFile("test_file.xml", b"<root><element>Test2</element></root>", content_type="application/xml")
        self.article_format = ArticleFormat.objects.create(
            article=self.article,
            format_name='pmc',
            version=1,
            file=self.test_file,
            valid=True,
            status="S",
        )

    def test_get_method(self):
        article_format = ArticleFormat.get(self.article, format_name='pmc', version=1)
        self.assertEqual(article_format.article,  self.article)
        self.assertEqual(article_format.format_name, 'pmc')
        self.assertEqual(article_format.version, 1)

    def test_create_classmethod(self):
        article_format = ArticleFormat.create(
            user=self.user,
            article=self.article,
            format_name='pubmed',
            version=1
        )
        self.assertEqual(article_format.article,  self.article)
        self.assertEqual(article_format.format_name, 'pubmed')
        self.assertEqual(article_format.version, 1)

    def test_get_method_raises_value_error(self):
        with self.assertRaises(ValueError) as context:
            ArticleFormat.get(self.article, format_name='pubmed')

        self.assertEqual(str(context.exception), "ArticleFormat.get requires article and format_name and version")

    def test_create_or_update_classmethod(self):
        article_format = ArticleFormat.create_or_update(
            user=self.user,
            article=self.article,
            format_name="pmc",
            version=1,
        )
        self.assertEqual(article_format.article,  self.article)
        self.assertEqual(article_format.format_name, 'pmc')
        self.assertEqual(article_format.version, 1)

    def test_save_file_method(self):
        filename = "0034-7094-rba-69-03-0227.xml"
        content = self.test_file
        content.seek(0)
        content_bytes = content.read()
        article_format = ArticleFormat.get(self.article, format_name='pmc', version=1)
        article_format.save_file(filename=filename, content=content_bytes)
        
        with article_format.file.open('rb') as f:
            saved_content = f.read()
        
        self.assertEqual(saved_content, content_bytes)

    def test_update_xml_in_save_file_method(self):
        filename = "0034-7094-rba-69-03-0227.xml"
        content = self.test_file
        content_update = self.test_file2
        content.seek(0)
        content_bytes = content.read()
        article_format = ArticleFormat.get(self.article, format_name='pmc', version=1)
        article_format.save_file(filename=filename, content=content_bytes)

        content_update.seek(0)
        content_update_bytes = content_update.read()
        article_format.save_file(filename=filename, content=content_update_bytes)

        with article_format.file.open('rb') as f:
            saved_content = f.read()

        self.assertEqual(saved_content, content_update_bytes)

    def test_save_format_xml_method(self):
        article_format = ArticleFormat.get(self.article, format_name='pmc', version=1)
        input_xml = "<article><element>Original</element></article>"
        
        filename = article_format.article.sps_pkg_name + ".xml"
        article_format.save_format_xml(format_xml=input_xml, filename=filename)
        with article_format.file.open('rb') as f:
            saved_content = f.read()
        self.assertEqual(saved_content, input_xml.encode('utf-8'))

        self.assertEqual(article_format.status, "S")
        self.assertEqual(article_format.report, None)
        self.assertEqual(article_format.version, 1)

