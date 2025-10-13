import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model

from article.models import Article, ArticleFormat
from article.search_indexes import ArticleOAIMODSIndex
from core.models import Language

User = get_user_model()


class MODSPhysicalDescriptionTestCase(TestCase):
    """
    Testes unitários para elemento physicalDescription MODS
    Testa forma, tipo de mídia e descrições físicas de recursos digitais
    """

    @classmethod
    def setUpTestData(cls):
        """Dados compartilhados entre testes para melhor performance"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

        cls.lang_pt = Language.objects.create(
            code2='pt',
            name='Português',
            creator=cls.user
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

    def _create_article_format(self, article, format_name, valid=True):
        """Helper para criar ArticleFormat"""
        return ArticleFormat.objects.create(
            article=article,
            format_name=format_name,
            valid=valid,
            version=1,
            creator=self.user
        )

    def test_physical_description_basic_structure(self):
        """Teste: estrutura básica do physicalDescription"""
        article = self._create_test_article()

        phys_desc = self.index.prepare_mods_physical_description(article)

        self.assertIsInstance(phys_desc, list)
        self.assertEqual(len(phys_desc), 1)

        phys_data = phys_desc[0]
        self.assertIsInstance(phys_data, dict)
        self.assertIn('form', phys_data)
        self.assertIn('internetMediaType', phys_data)
        self.assertIn('extent', phys_data)
        self.assertIn('digitalOrigin', phys_data)

    def test_form_element_structure(self):
        """Teste: estrutura do elemento form"""
        article = self._create_test_article()

        phys_desc = self.index.prepare_mods_physical_description(article)
        form_data = phys_desc[0]['form']

        self.assertIsInstance(form_data, dict)
        self.assertIn('authority', form_data)
        self.assertEqual(form_data['authority'], 'marcform')
        self.assertIn('text', form_data)
        self.assertEqual(form_data['text'], 'electronic')

    def test_internet_media_type_default(self):
        """Teste: tipos de mídia padrão HTML e PDF"""
        article = self._create_test_article()

        phys_desc = self.index.prepare_mods_physical_description(article)
        media_types = phys_desc[0]['internetMediaType']

        self.assertIsInstance(media_types, list)
        self.assertIn('text/html', media_types)
        self.assertIn('application/pdf', media_types)

    def test_internet_media_type_with_crossref_format(self):
        """Teste: tipo de mídia com formato CrossRef"""
        article = self._create_test_article()
        self._create_article_format(article, 'crossref', valid=True)

        phys_desc = self.index.prepare_mods_physical_description(article)
        media_types = phys_desc[0]['internetMediaType']

        self.assertIn('application/vnd.crossref.unixsd+xml', media_types)
        self.assertIn('text/html', media_types)
        self.assertIn('application/pdf', media_types)

    def test_internet_media_type_with_pubmed_format(self):
        """Teste: tipo de mídia com formato PubMed"""
        article = self._create_test_article()
        self._create_article_format(article, 'pubmed', valid=True)

        phys_desc = self.index.prepare_mods_physical_description(article)
        media_types = phys_desc[0]['internetMediaType']

        self.assertIn('application/vnd.pubmed+xml', media_types)

    def test_internet_media_type_with_pmc_format(self):
        """Teste: tipo de mídia com formato PMC"""
        article = self._create_test_article()
        self._create_article_format(article, 'pmc', valid=True)

        phys_desc = self.index.prepare_mods_physical_description(article)
        media_types = phys_desc[0]['internetMediaType']

        self.assertIn('application/vnd.pmc+xml', media_types)

    def test_internet_media_type_with_multiple_formats(self):
        """Teste: múltiplos formatos válidos"""
        article = self._create_test_article()
        self._create_article_format(article, 'crossref', valid=True)
        self._create_article_format(article, 'pubmed', valid=True)
        self._create_article_format(article, 'pmc', valid=True)

        phys_desc = self.index.prepare_mods_physical_description(article)
        media_types = phys_desc[0]['internetMediaType']

        self.assertIn('application/vnd.crossref.unixsd+xml', media_types)
        self.assertIn('application/vnd.pubmed+xml', media_types)
        self.assertIn('application/vnd.pmc+xml', media_types)
        self.assertIn('text/html', media_types)
        self.assertIn('application/pdf', media_types)

    def test_internet_media_type_ignores_invalid_formats(self):
        """Teste: formatos inválidos são ignorados"""
        article = self._create_test_article()
        self._create_article_format(article, 'crossref', valid=False)
        self._create_article_format(article, 'pubmed', valid=True)

        phys_desc = self.index.prepare_mods_physical_description(article)
        media_types = phys_desc[0]['internetMediaType']

        self.assertNotIn('application/vnd.crossref.unixsd+xml', media_types)
        self.assertIn('application/vnd.pubmed+xml', media_types)

    def test_internet_media_type_no_duplicates(self):
        """Teste: não há tipos de mídia duplicados"""
        article = self._create_test_article()
        self._create_article_format(article, 'html', valid=True)
        self._create_article_format(article, 'pdf', valid=True)

        phys_desc = self.index.prepare_mods_physical_description(article)
        media_types = phys_desc[0]['internetMediaType']

        # Verificar que não há duplicatas
        self.assertEqual(len(media_types), len(set(media_types)))

        # HTML e PDF aparecem apenas uma vez
        self.assertEqual(media_types.count('text/html'), 1)
        self.assertEqual(media_types.count('application/pdf'), 1)

    def test_extent_with_numeric_pages(self):
        """Teste: extensão com páginas numéricas"""
        article = self._create_test_article(first_page='10', last_page='25')

        phys_desc = self.index.prepare_mods_physical_description(article)
        extent = phys_desc[0]['extent']

        self.assertEqual(extent, '16 pages')

    def test_extent_with_single_page(self):
        """Teste: extensão com página única"""
        article = self._create_test_article(first_page='10', last_page='10')

        phys_desc = self.index.prepare_mods_physical_description(article)
        extent = phys_desc[0]['extent']

        self.assertEqual(extent, '1 pages')

    def test_extent_with_non_numeric_pages(self):
        """Teste: extensão com páginas não numéricas"""
        article = self._create_test_article(first_page='e123', last_page='e156')

        phys_desc = self.index.prepare_mods_physical_description(article)
        extent = phys_desc[0]['extent']

        self.assertEqual(extent, 'pages e123-e156')

    def test_extent_with_only_first_page(self):
        """Teste: extensão apenas com primeira página"""
        article = self._create_test_article(first_page='42', last_page=None)

        phys_desc = self.index.prepare_mods_physical_description(article)
        extent = phys_desc[0]['extent']

        self.assertEqual(extent, 'page 42')

    def test_extent_without_pages(self):
        """Teste: extensão sem páginas definidas"""
        article = self._create_test_article(first_page=None, last_page=None)

        phys_desc = self.index.prepare_mods_physical_description(article)
        extent = phys_desc[0]['extent']

        self.assertEqual(extent, '1 online resource')

    def test_extent_with_roman_numerals(self):
        """Teste: extensão com numeração romana"""
        article = self._create_test_article(first_page='iv', last_page='xii')

        phys_desc = self.index.prepare_mods_physical_description(article)
        extent = phys_desc[0]['extent']

        self.assertEqual(extent, 'pages iv-xii')

    def test_digital_origin_always_born_digital(self):
        """Teste: digitalOrigin sempre é born digital"""
        article = self._create_test_article()

        phys_desc = self.index.prepare_mods_physical_description(article)
        digital_origin = phys_desc[0]['digitalOrigin']

        self.assertEqual(digital_origin, 'born digital')

    def test_complete_structure_all_elements(self):
        """Teste: estrutura completa com todos os elementos"""
        article = self._create_test_article(first_page='100', last_page='115')
        self._create_article_format(article, 'crossref', valid=True)
        self._create_article_format(article, 'pubmed', valid=True)

        phys_desc = self.index.prepare_mods_physical_description(article)

        self.assertEqual(len(phys_desc), 1)

        phys_data = phys_desc[0]

        # Verificar form
        self.assertEqual(phys_data['form']['authority'], 'marcform')
        self.assertEqual(phys_data['form']['text'], 'electronic')

        # Verificar internetMediaType
        self.assertIn('text/html', phys_data['internetMediaType'])
        self.assertIn('application/pdf', phys_data['internetMediaType'])
        self.assertIn('application/vnd.crossref.unixsd+xml', phys_data['internetMediaType'])
        self.assertIn('application/vnd.pubmed+xml', phys_data['internetMediaType'])

        # Verificar extent
        self.assertEqual(phys_data['extent'], '16 pages')

        # Verificar digitalOrigin
        self.assertEqual(phys_data['digitalOrigin'], 'born digital')

    def test_return_type_consistency(self):
        """Teste: consistência do tipo de retorno"""
        test_cases = [
            ('minimal', lambda: self._create_test_article()),
            ('with_formats', lambda: self._create_article_with_formats()),
            ('with_pages', lambda: self._create_test_article(first_page='1', last_page='10')),
        ]

        for test_name, article_creator in test_cases:
            with self.subTest(test=test_name):
                article = article_creator()

                phys_desc = self.index.prepare_mods_physical_description(article)

                self.assertIsInstance(phys_desc, list)
                self.assertEqual(len(phys_desc), 1)
                self.assertIsInstance(phys_desc[0], dict)

    def test_media_types_sorted(self):
        """Teste: tipos de mídia são ordenados"""
        article = self._create_test_article()
        self._create_article_format(article, 'pmc', valid=True)
        self._create_article_format(article, 'crossref', valid=True)
        self._create_article_format(article, 'pubmed', valid=True)

        phys_desc = self.index.prepare_mods_physical_description(article)
        media_types = phys_desc[0]['internetMediaType']

        # Verificar que está ordenado
        self.assertEqual(media_types, sorted(media_types))

    def test_edge_case_empty_format_name(self):
        """Teste: formato com nome vazio"""
        article = self._create_test_article()

        article_format = ArticleFormat.objects.create(
            article=article,
            format_name='',
            valid=True,
            version=1,
            creator=self.user
        )

        phys_desc = self.index.prepare_mods_physical_description(article)
        media_types = phys_desc[0]['internetMediaType']

        # Deve ter apenas os padrões
        self.assertIn('text/html', media_types)
        self.assertIn('application/pdf', media_types)

    def test_edge_case_none_format_name(self):
        """Teste: formato com nome None"""
        article = self._create_test_article()

        article_format = ArticleFormat.objects.create(
            article=article,
            format_name=None,
            valid=True,
            version=1,
            creator=self.user
        )

        phys_desc = self.index.prepare_mods_physical_description(article)

        # Não deve causar erro
        self.assertIsInstance(phys_desc, list)

    def test_edge_case_unknown_format_name(self):
        """Teste: formato desconhecido"""
        article = self._create_test_article()
        self._create_article_format(article, 'unknown_format', valid=True)

        phys_desc = self.index.prepare_mods_physical_description(article)
        media_types = phys_desc[0]['internetMediaType']

        # Deve ter apenas os padrões
        self.assertIn('text/html', media_types)
        self.assertIn('application/pdf', media_types)
        # Formato desconhecido não deve ser adicionado
        self.assertEqual(len([mt for mt in media_types if 'unknown' in mt]), 0)

    def test_method_isolation(self):
        """Teste: método não modifica objeto"""
        article = self._create_test_article(first_page='1', last_page='10')
        original_first = article.first_page
        original_last = article.last_page

        phys_desc = self.index.prepare_mods_physical_description(article)

        self.assertEqual(article.first_page, original_first)
        self.assertEqual(article.last_page, original_last)

    def test_multiple_calls_consistency(self):
        """Teste: consistência entre múltiplas chamadas"""
        article = self._create_test_article(first_page='5', last_page='15')
        self._create_article_format(article, 'crossref', valid=True)

        result1 = self.index.prepare_mods_physical_description(article)
        result2 = self.index.prepare_mods_physical_description(article)
        result3 = self.index.prepare_mods_physical_description(article)

        self.assertEqual(result1, result2)
        self.assertEqual(result2, result3)

    def _create_article_with_formats(self):
        """Helper para criar artigo com múltiplos formatos"""
        article = self._create_test_article()
        self._create_article_format(article, 'crossref', valid=True)
        self._create_article_format(article, 'pubmed', valid=True)
        return article

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_physical_description.MODSPhysicalDescriptionTestCase --parallel 2 -v 2
