# Biblioteca padrão
import os
import tempfile
from io import BytesIO
from datetime import datetime

# Terceiros
from freezegun import freeze_time
from lxml import etree
from unittest.mock import patch, PropertyMock
from django.test import TestCase
from django.utils.timezone import make_aware
from django.contrib.auth import get_user_model

# Aplicações locais
from article.utils.xml_loader import load_xml
from article.models import Article, ArticleFormat
from article.tasks import (
    remove_duplicate_articles,
    normalize_stored_email,
    get_researcher_identifier_unnormalized,
    generate_article_format,
)
from pid_provider.provider import PidProvider
from researcher.models import ResearcherIdentifier

User = get_user_model()


class RemoveDuplicateArticlesTest(TestCase):
    def create_article_at_time(self, dt, v3):
        @freeze_time(dt)
        def create_article():
            Article.objects.create(
                pid_v3=v3,
                created=make_aware(datetime.strptime(dt, "%Y-%m-%d"))
            )
        create_article()

    def test_remove_duplicates_keeps_earliest_article(self):
        self.create_article_at_time("2023-01-01", "pid1")
        self.create_article_at_time("2023-01-02", "pid1")
        self.create_article_at_time("2023-01-03", "pid1")
        remove_duplicate_articles()
        self.assertEqual(Article.objects.count(), 1)
        self.assertEqual(
            Article.objects.first().created,
            make_aware(datetime(2023, 1, 1))
        )

    def test_no_removal_if_only_one_article(self):
        self.create_article_at_time("2023-01-01", "pid1")
        remove_duplicate_articles()
        self.assertEqual(Article.objects.count(), 1)
        self.assertEqual(
            Article.objects.first().created,
            make_aware(datetime(2023, 1, 1))
        )

    def test_remove_duplicates_for_multiple_pids(self):
        self.create_article_at_time("2022-06-03", "pid2")
        self.create_article_at_time("2022-06-04", "pid2")
        self.create_article_at_time("2022-07-08", "pid3")
        self.create_article_at_time("2022-06-14", "pid3")
        remove_duplicate_articles()
        self.assertEqual(
            Article.objects.filter(pid_v3="pid2").count(),
            1
        )
        self.assertEqual(
            Article.objects.filter(pid_v3="pid3").count(),
            1
        )
        self.assertEqual(
            Article.objects.get(pid_v3="pid2").created,
            make_aware(datetime(2022, 6, 3))
        )
        self.assertEqual(
            Article.objects.get(pid_v3="pid3").created,
            make_aware(datetime(2022, 6, 14))
        )


class NormalizeEmailResearcherIdentifierTest(TestCase):
    def setUp(self):
        self.emails = [
            '<a href="mailto:jgarrido@ucv.cl">jgarrido@ucv.cl</a>',
            '<a href="mailto:gagopa39@hotmail.com">gagopa39@hotmail.com</a>',
            ' herbet@ufs.br',
            'pilosaperez@gmail.com.',
            'cortes- camarillo@hotmail.com',
            'ulrikekeyser@upn162-zamora.edu.mx',
            'cortescamarillo@hotmail.com',
            'candelariasgro@yahoo.com',
            'mailto:user@hotmail.com">gagopa39@hotmail.com</a>',
        ]
        self.orcids = [
            '0000-0002-9147-0547',
            '0000-0003-3622-3428',
            '0000-0002-4842-3331',
            '0000-0003-1314-4073',
        ]
        ResearcherIdentifier.objects.bulk_create([
            ResearcherIdentifier(identifier=email, source_name="EMAIL")
            for email in self.emails
        ])
        ResearcherIdentifier.objects.bulk_create([
            ResearcherIdentifier(identifier=orcid, source_name="ORCID")
            for orcid in self.orcids
        ])

    def test_normalize_stored_email(self):
        unnormalized = get_researcher_identifier_unnormalized()
        self.assertEqual(unnormalized.count(), 6)

        normalize_stored_email()

        esperados = [
            'jgarrido@ucv.cl',
            'gagopa39@hotmail.com',
            'herbet@ufs.br',
            'pilosaperez@gmail.com',
            'cortes-camarillo@hotmail.com',
            'user@hotmail.com',
        ]
        for email in esperados:
            with self.subTest(email=email):
                self.assertTrue(
                    ResearcherIdentifier.objects.filter(identifier=email).exists(),
                    f"E-mail '{email}' não foi normalizado"
                )


class XmlLoaderTest(TestCase):
    def setUp(self):
        # XML mínimo para testes
        self.xml_string = '<root><child>value</child></root>'
        self.xml_bytes = self.xml_string.encode('utf-8')

    def test_load_from_string(self):
        root = load_xml(xml=self.xml_string)
        self.assertIsInstance(root, etree._Element)
        self.assertEqual(root.tag, 'root')

    def test_load_from_bytes(self):
        root = load_xml(xml=self.xml_bytes)
        self.assertIsInstance(root, etree._Element)
        self.assertEqual(root.find('child').text, 'value')

    def test_load_from_file_path(self):
        fd, path = tempfile.mkstemp(suffix='.xml')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(self.xml_string)
            root = load_xml(file_path=path)
            self.assertEqual(root.find('child').tag, 'child')
        finally:
            os.remove(path)

    def test_load_from_file_obj(self):
        bio = BytesIO(self.xml_bytes)
        root = load_xml(file_obj=bio)
        self.assertEqual(root.tag, 'root')

    def test_load_from_article_model(self):
        art = Article.objects.create(pid_v3='testpid')
        tree = etree.fromstring(self.xml_string)
        with self.subTest('fonte article'):
            original = PidProvider.get_xmltree
            PidProvider.get_xmltree = staticmethod(lambda pid: tree)
            try:
                root = load_xml(article=art)
                self.assertEqual(root.find('child').text, 'value')
            finally:
                PidProvider.get_xmltree = original

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            load_xml()
        with self.assertRaises(ValueError):
            load_xml(xml=self.xml_string, file_obj=BytesIO(self.xml_bytes))


class ArticleFormatGenerationTest(TestCase):
    def setUp(self):
        self.article = Article.objects.create(
            pid_v3="jvchwYdtTvVc3pXqgZjyb5g",
            sps_pkg_name="jvchwYdtTvVc3pXqgZjyb5g"
        )

    def test_should_generate_all_formats(self):
        xml_string = """
        <article>
            <front>
                <journal-meta>
                    <publisher>
                        <publisher-name>Exemplo</publisher-name>
                    </publisher>
                </journal-meta>
            </front>
            <back>
                <ref-list>
                    <ref><mixed-citation><year>2020</year></mixed-citation></ref>
                </ref-list>
            </back>
        </article>
        """
        xml_tree = etree.fromstring(xml_string)
        with patch.object(Article, "xmltree", new_callable=PropertyMock) as mock_xmltree:
            mock_xmltree.return_value = xml_tree
            generate_article_format(article_id=self.article.id)

        formats = ArticleFormat.objects.filter(article=self.article)
        self.assertEqual(formats.count(), 3)
        for fmt in formats:
            self.assertTrue(bool(fmt.file))
            self.assertIsNone(fmt.report)
            self.assertTrue(fmt.valid)


class ArticleFormatModelTest(TestCase):
    """Testa a geração de formatos XML para um Article."""
    def setUp(self):
        self.article = Article.objects.create(
            pid_v3="fmtTest123",
            sps_pkg_name="fmtTest123"
        )
        self.xml_tree = etree.fromstring('<root><data>test</data></root>')
        patcher = patch.object(Article, 'xmltree', new_callable=PropertyMock)
        self.mock_xml = patcher.start()
        self.mock_xml.return_value = self.xml_tree
        self.addCleanup(patcher.stop)

    def test_generate_all_formats_creates_instances(self):
        # stub pipelines para retornarem conteúdo XML simples
        for name in ArticleFormat.PIPELINES.keys():
            ArticleFormat.PIPELINES[name] = lambda tree, name=name: f'<{name}>{name}</{name}>'

        ArticleFormat.generate_formats(user=None, article=self.article)

        formats = ArticleFormat.objects.filter(article=self.article)
        self.assertEqual(formats.count(), len(ArticleFormat.PIPELINES))
        for fmt in formats:
            self.assertIn(fmt.format_name, ArticleFormat.PIPELINES)
            self.assertEqual(fmt.version, 1)
            self.assertTrue(fmt.valid)
            self.assertIsNone(fmt.report)
            self.assertTrue(fmt.file.name.endswith('.xml'))

    def test_generate_with_indexed_check(self):
        Article.is_indexed_at = lambda self, acronym: acronym == 'pubmed'
        ArticleFormat.PIPELINES = {
            'crossref': lambda tree: '<crossref/>',
            'pubmed':   lambda tree: '<pubmed/>',
            'pmc':      lambda tree: '<pmc/>'
        }
        ArticleFormat.generate_formats(user=None, article=self.article, indexed_check=True)

        formats = ArticleFormat.objects.filter(article=self.article)
        self.assertEqual(formats.count(), 1)
        fmt = formats.first()
        self.assertEqual(fmt.format_name, 'pubmed')
        self.assertTrue(fmt.valid)

    def test_pipeline_error_sets_invalid(self):
        ArticleFormat.PIPELINES = {'pubmed': lambda tree: (_ for _ in ()).throw(ValueError('fail'))}
        ArticleFormat.generate_formats(user=None, article=self.article)

        fmt = ArticleFormat.objects.get(article=self.article, format_name='pubmed')
        self.assertFalse(fmt.valid)
        self.assertIsNotNone(fmt.report)
        self.assertFalse(bool(fmt.file))
