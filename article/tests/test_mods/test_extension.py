import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model

from article.models import Article
from article.search_indexes import ArticleOAIMODSIndex
from article import choices

User = get_user_model()


class MODSExtensionTestCase(TestCase):
    """
    Testes unitários mínimos para elemento extension MODS
    Testa metadados técnicos específicos do SciELO
    """

    @classmethod
    def setUpTestData(cls):
        """Dados compartilhados entre testes para melhor performance"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

    def setUp(self):
        """Configuração mínima por teste"""
        self.index = ArticleOAIMODSIndex()

    def _create_test_article(self, **kwargs):
        """Helper otimizado para criar artigo de teste"""
        defaults = {
            'sps_pkg_name': f'test-{uuid.uuid4().hex[:12]}',
            'pid_v3': f'test-{uuid.uuid4().hex[:12]}',
            'article_type': 'research-article',
            'creator': self.user
        }
        defaults.update(kwargs)
        return Article.objects.create(**defaults)

    def test_extension_basic_structure(self):
        """Teste: estrutura básica do extension"""
        article = self._create_test_article()

        extensions = self.index.prepare_mods_extension(article)

        self.assertIsInstance(extensions, list)
        self.assertEqual(len(extensions), 1)

        extension = extensions[0]
        self.assertIsInstance(extension, dict)
        self.assertIn('type', extension)
        self.assertEqual(extension['type'], 'scielo')
        self.assertIn('scielo', extension)

    def test_extension_with_sps_pkg_name(self):
        """Teste: extension com sps_pkg_name"""
        pkg_name = 'test-pkg-2024-v1-n1-001'
        article = self._create_test_article(sps_pkg_name=pkg_name)

        extensions = self.index.prepare_mods_extension(article)
        scielo_data = extensions[0]['scielo']

        self.assertIn('sps_pkg_name', scielo_data)
        self.assertEqual(scielo_data['sps_pkg_name'], pkg_name)

    def test_extension_with_data_status(self):
        """Teste: extension com data_status"""
        article = self._create_test_article(data_status=choices.DATA_STATUS_PUBLIC)

        extensions = self.index.prepare_mods_extension(article)
        scielo_data = extensions[0]['scielo']

        self.assertIn('data_status', scielo_data)
        self.assertEqual(scielo_data['data_status'], choices.DATA_STATUS_PUBLIC)

    def test_extension_with_valid_true(self):
        """Teste: extension com valid=True"""
        article = self._create_test_article(valid=True)

        extensions = self.index.prepare_mods_extension(article)
        scielo_data = extensions[0]['scielo']

        self.assertIn('valid', scielo_data)
        self.assertEqual(scielo_data['valid'], 'true')

    def test_extension_with_valid_false(self):
        """Teste: extension com valid=False"""
        article = self._create_test_article(valid=False)

        extensions = self.index.prepare_mods_extension(article)
        scielo_data = extensions[0]['scielo']

        self.assertIn('valid', scielo_data)
        self.assertEqual(scielo_data['valid'], 'false')

    def test_extension_complete_data(self):
        """Teste: extension com todos os dados"""
        article = self._create_test_article(
            sps_pkg_name='complete-pkg-test',
            data_status=choices.DATA_STATUS_PUBLIC,
            valid=True
        )

        extensions = self.index.prepare_mods_extension(article)
        scielo_data = extensions[0]['scielo']

        self.assertEqual(scielo_data['sps_pkg_name'], 'complete-pkg-test')
        self.assertEqual(scielo_data['data_status'], choices.DATA_STATUS_PUBLIC)
        self.assertEqual(scielo_data['valid'], 'true')

    def test_extension_empty_when_no_data(self):
        """Teste: extension vazio quando não há dados técnicos"""
        article = self._create_test_article(
            sps_pkg_name=None,
            data_status=None,
            valid=None
        )

        extensions = self.index.prepare_mods_extension(article)

        self.assertEqual(len(extensions), 0)

    def test_extension_partial_data(self):
        """Teste: extension com dados parciais"""
        article = self._create_test_article(
            sps_pkg_name='partial-pkg',
            data_status=None,
            valid=None
        )

        extensions = self.index.prepare_mods_extension(article)
        scielo_data = extensions[0]['scielo']

        self.assertIn('sps_pkg_name', scielo_data)
        self.assertNotIn('data_status', scielo_data)
        self.assertNotIn('valid', scielo_data)

    def test_return_type_consistency(self):
        """Teste: consistência do tipo de retorno"""
        article = self._create_test_article()

        extensions = self.index.prepare_mods_extension(article)

        self.assertIsInstance(extensions, list)
        for extension in extensions:
            self.assertIsInstance(extension, dict)

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_extension.MODSExtensionTestCase --parallel 2 -v 2
