from lxml import etree
from freezegun import freeze_time
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django_test_migrations.migrator import Migrator
from datetime import datetime
from django.utils.timezone import make_aware
from unittest.mock import patch, PropertyMock

from article.models import Article, ArticleFormat
from article.tasks import remove_duplicate_articles, convert_xml_to_pubmed_or_pmc_formats, convert_xml_to_crossref_format
from core.users.models import User
from doi.models import DOI
from doi_manager.models import CrossRefConfiguration


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

        self.test_file = SimpleUploadedFile("test_file.xml", b"<article><element>Test</element></article>", content_type="application/xml")
        self.test_file2 = SimpleUploadedFile("test_file2.xml", b"<article><element>Test2</element></article>", content_type="application/xml")
        self.article_format = ArticleFormat.objects.create(
            article=self.article,
            format_name='pmc',
            version=1,
            file=self.test_file,
            valid=True,
            status="S",
        )

    def verify_fields_model_article_format(self, article_format, version, format_name=None, status=None, file=None):
        self.assertEqual(article_format.article,  self.article)
        if format_name:
            self.assertEqual(article_format.format_name, format_name)
        self.assertEqual(article_format.version, version)
        self.assertEqual(article_format.report, None)
        if status:
            self.assertEqual(article_format.status, status)
    
    def test_get_method(self):
        article_format = ArticleFormat.get(self.article, format_name='pmc', version=1)
        self.verify_fields_model_article_format(article_format=article_format, format_name='pmc', version=1)

    def test_create_classmethod(self):
        article_format = ArticleFormat.create(
            user=self.user,
            article=self.article,
            format_name='pubmed',
            version=1
        )
        self.verify_fields_model_article_format(article_format=article_format, format_name='pubmed', version=1)

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
        self.verify_fields_model_article_format(article_format=article_format, format_name='pmc', version=1)
    
    def convert_and_compare_xml(self, article_format, filename, xml_content):
        article_format.save_file(filename=filename, content=xml_content)
        with article_format.file.open("rb") as f:
            saved_content = f.read()
        self.assertEqual(etree.tostring(etree.fromstring(saved_content), encoding="utf-8"),
                         etree.tostring(xml_content, encoding="utf-8"))

    def test_save_file_method(self):
        filename = "0034-7094-rba-69-03-0227.xml"
        article_format = ArticleFormat.get(self.article, format_name='pmc', version=1)
        self.test_file.seek(0)
        input_xml = etree.fromstring(self.test_file.read())
        self.convert_and_compare_xml(article_format=article_format, filename=filename, xml_content=input_xml)

    def test_update_xml_in_save_file_method(self):
        filename = "0034-7094-rba-69-03-0227.xml"
        self.test_file.seek(0)
        input_xml = etree.fromstring(self.test_file.read())

        article_format = ArticleFormat.get(self.article, format_name='pmc', version=1)
        self.convert_and_compare_xml(article_format=article_format, filename=filename, xml_content=input_xml)

        self.test_file2.seek(0)
        update_xml = etree.fromstring(self.test_file2.read())
        self.convert_and_compare_xml(article_format=article_format, filename=filename, xml_content=update_xml)

    def test_save_format_xml_method(self):
        article_format = ArticleFormat.get(self.article, format_name='pmc', version=1)
        input_xml = etree.fromstring("<article><element>Test</element></article>")
        filename = article_format.article.sps_pkg_name + ".xml"
        article_format.save_format_xml(format_xml=input_xml, filename=filename, status="S")
        with article_format.file.open('rb') as f:
            saved_content = f.read()
        self.assertEqual(saved_content, etree.tostring(input_xml, encoding="utf-8"))
        self.verify_fields_model_article_format(article_format=article_format, status="S", version=1)

class TasksConvertXmlFormatsTest(TestCase):
    def setUp(self):
        self.doi = DOI.objects.create(
            value="10.1000.10/123456"
        )
        self.article = Article.objects.create(
            pid_v3="P3swRmPHQfy37r9xRbLCw8G",
            sps_pkg_name="0001-3714-rm-30-04-299",
        )
        self.user = User.objects.create(
            username="admin",
        )

        self.input_xml = etree.fromstring("<article><element>Original PMC</element></article>")
        self.modified_xml = etree.fromstring("<article><element>Modified PMC</element></article>")
    
    def verify_article_format(self, status, version, pid_v3=None, report=None, file_exists=True):
        self.assertEqual(ArticleFormat.objects.count(), 1)
        article_format = ArticleFormat.objects.first()
        self.assertEqual(article_format.article.pid_v3, pid_v3 or self.article.pid_v3)
        self.assertEqual(article_format.status, status)
        self.assertEqual(article_format.version, version)
        if report:
            self.assertEqual(article_format.report, report)
        if file_exists:
            with article_format.file.open('rb') as f:
                content = f.read()
            self.assertEqual(content, etree.tostring(self.modified_xml, encoding="utf-8"))
        else:
            self.assertFalse(article_format.file)
    
    @patch('article.models.Article.xmltree', new_callable=PropertyMock)
    @patch('article.tasks.pmc.pipeline_pmc')
    def test_convert_xml_to_pmc_formats(self, mock_pipeline_pmc, mock_property_xmltree):
        mock_property_xmltree.return_value = self.input_xml
        mock_pipeline_pmc.return_value = self.modified_xml

        convert_xml_to_pubmed_or_pmc_formats(pid_v3=self.article.pid_v3, format_name="pmc", username="admin")
        mock_pipeline_pmc.assert_called_once_with(mock_property_xmltree.return_value)
        self.verify_article_format(status="S", version=1)

    
    @patch('article.models.Article.xmltree', new_callable=PropertyMock)
    @patch('article.tasks.pubmed.pipeline_pubmed')
    def test_convert_xml_to_pubmed_formats(self, mock_pipeline_pubmed, mock_property_xmltree):
        mock_property_xmltree.return_value = self.input_xml
        mock_pipeline_pubmed.return_value = self.modified_xml

        convert_xml_to_pubmed_or_pmc_formats(pid_v3=self.article.pid_v3, format_name="pubmed", username="admin")
        mock_pipeline_pubmed.assert_called_once_with(mock_property_xmltree.return_value)
        self.verify_article_format(status="S", version=1)


    @patch('doi_manager.models.CrossRefConfiguration.get_data', return_value=dict())
    @patch('article.models.Article.xmltree', new_callable=PropertyMock)
    @patch('article.tasks.crossref.pipeline_crossref')
    def test_convert_xml_to_crossref_formats(self, mock_pipeline_crossref, mock_property_xmltree, mock_get_data):
        self.article.doi.add(self.doi)
        mock_property_xmltree.return_value = self.input_xml
        mock_pipeline_crossref.return_value = self.modified_xml

        convert_xml_to_crossref_format(pid_v3=self.article.pid_v3, format_name="crossref", username="admin")
        self.verify_article_format(status="S", version=1)


    def test_convert_xml_to_crossref_formats_without_doi(self):
        convert_xml_to_crossref_format(pid_v3=self.article.pid_v3, format_name="crossref", username="admin")
        expected_msg = {"exception_msg": f"Unable to format because the article {self.article.pid_v3} has no DOI associated with it"}
        self.verify_article_format(status="E", version=1, file_exists=False, report=expected_msg)


    @patch('doi_manager.models.CrossRefConfiguration.get_data')
    def test_convert_xml_to_crossref_formats_missing_crossref_configuration(self, mock_get_data):
        self.article.doi.add(self.doi)
        mock_get_data.side_effect = CrossRefConfiguration.DoesNotExist
        convert_xml_to_crossref_format(pid_v3=self.article.pid_v3, format_name="crossref", username="admin")
        expected_prefix = '10.1000.10'
        mock_get_data.assert_called_once_with(expected_prefix)

