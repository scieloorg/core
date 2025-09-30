import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model

from article.models import Article
from article.search_indexes import ArticleOAIMODSIndex

User = get_user_model()


class MODSGenreTestCase(TestCase):
    """
    Testes unitários para elemento genre MODS
    Valida implementação real em search_indexes.py
    """

    @classmethod
    def setUpTestData(cls):
        """Dados compartilhados entre testes"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

    def setUp(self):
        """Configuração por teste"""
        self.index = ArticleOAIMODSIndex()

    def _create_test_article(self, **kwargs):
        """Helper para criar artigo"""
        defaults = {
            'sps_pkg_name': f'test-pkg-{uuid.uuid4().hex[:12]}',
            'pid_v3': f'pid3-{uuid.uuid4().hex[:12]}',
            'creator': self.user
        }
        defaults.update(kwargs)
        return Article.objects.create(**defaults)

    # GRUPO 1: COMPORTAMENTO BÁSICO

    def test_genre_returns_list(self):
        """Sempre retorna lista"""
        article = self._create_test_article()
        result = self.index.prepare_mods_genre(article)
        self.assertIsInstance(result, list)

    def test_genre_empty_when_no_type(self):
        """Lista vazia quando article_type é None"""
        article = self._create_test_article(article_type=None)
        result = self.index.prepare_mods_genre(article)
        self.assertEqual(result, [])

    def test_genre_empty_when_empty_string(self):
        """Lista vazia quando article_type é string vazia"""
        article = self._create_test_article(article_type='')
        result = self.index.prepare_mods_genre(article)
        self.assertEqual(result, [])

    # GRUPO 2: MAPEAMENTOS IMPLEMENTADOS (Title Case)

    def test_genre_research_article(self):
        """research-article → 'Research Article'"""
        article = self._create_test_article(article_type='research-article')
        result = self.index.prepare_mods_genre(article)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['authority'], 'scielo')
        self.assertEqual(result[0]['text'], 'Research Article')

    def test_genre_review_article(self):
        """review-article → 'Review Article'"""
        article = self._create_test_article(article_type='review-article')
        result = self.index.prepare_mods_genre(article)
        self.assertEqual(result[0]['text'], 'Review Article')

    def test_genre_case_report(self):
        """case-report → 'Case Report'"""
        article = self._create_test_article(article_type='case-report')
        result = self.index.prepare_mods_genre(article)
        self.assertEqual(result[0]['text'], 'Case Report')

    def test_genre_editorial(self):
        """editorial → 'Editorial'"""
        article = self._create_test_article(article_type='editorial')
        result = self.index.prepare_mods_genre(article)
        self.assertEqual(result[0]['text'], 'Editorial')

    def test_genre_letter(self):
        """letter → 'Letter to the Editor'"""
        article = self._create_test_article(article_type='letter')
        result = self.index.prepare_mods_genre(article)
        self.assertEqual(result[0]['text'], 'Letter to the Editor')

    def test_genre_brief_report(self):
        """brief-report → 'Brief Communication'"""
        article = self._create_test_article(article_type='brief-report')
        result = self.index.prepare_mods_genre(article)
        self.assertEqual(result[0]['text'], 'Brief Communication')

    def test_genre_correction(self):
        """correction → 'Correction'"""
        article = self._create_test_article(article_type='correction')
        result = self.index.prepare_mods_genre(article)
        self.assertEqual(result[0]['text'], 'Correction')

    def test_genre_retraction(self):
        """retraction → 'Retraction Notice'"""
        article = self._create_test_article(article_type='retraction')
        result = self.index.prepare_mods_genre(article)
        self.assertEqual(result[0]['text'], 'Retraction Notice')

    # GRUPO 3: FALLBACK (Converte para Title Case)

    def test_genre_unknown_type_titlecase(self):
        """Tipo desconhecido: 'book-review' → 'Book Review'"""
        article = self._create_test_article(article_type='book-review')
        result = self.index.prepare_mods_genre(article)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['text'], 'Book Review')

    def test_genre_custom_type_converted(self):
        """Tipos customizados são convertidos para Title Case"""
        article = self._create_test_article(article_type='rapid-communication')
        result = self.index.prepare_mods_genre(article)
        self.assertEqual(result[0]['text'], 'Rapid Communication')

    # GRUPO 4: ESTRUTURA DO RETORNO

    def test_genre_structure_complete(self):
        """Verifica estrutura completa do dicionário"""
        article = self._create_test_article(article_type='editorial')
        result = self.index.prepare_mods_genre(article)

        self.assertEqual(set(result[0].keys()), {'authority', 'text'})
        self.assertIsInstance(result[0]['authority'], str)
        self.assertIsInstance(result[0]['text'], str)

    def test_genre_authority_always_scielo(self):
        """Authority sempre é 'scielo'"""
        types = ['research-article', 'editorial', 'unknown-type']

        for article_type in types:
            with self.subTest(article_type=article_type):
                article = self._create_test_article(article_type=article_type)
                result = self.index.prepare_mods_genre(article)
                self.assertEqual(result[0]['authority'], 'scielo')

    # GRUPO 5: CONSISTÊNCIA

    def test_genre_idempotent(self):
        """Múltiplas chamadas retornam mesmo resultado"""
        article = self._create_test_article(article_type='research-article')

        result1 = self.index.prepare_mods_genre(article)
        result2 = self.index.prepare_mods_genre(article)
        result3 = self.index.prepare_mods_genre(article)

        self.assertEqual(result1, result2)
        self.assertEqual(result2, result3)

    def test_genre_no_side_effects(self):
        """Não modifica o objeto Article"""
        article = self._create_test_article(article_type='editorial')
        original_type = article.article_type

        self.index.prepare_mods_genre(article)

        article.refresh_from_db()
        self.assertEqual(article.article_type, original_type)

    # GRUPO 6: MAPEAMENTO COMPLETO (REGRESSÃO)

    def test_genre_all_mappings(self):
        """Valida todos os mapeamentos implementados"""
        mappings = {
            'research-article': 'Research Article',
            'review-article': 'Review Article',
            'case-report': 'Case Report',
            'editorial': 'Editorial',
            'letter': 'Letter to the Editor',
            'brief-report': 'Brief Communication',
            'correction': 'Correction',
            'retraction': 'Retraction Notice',
        }

        for input_type, expected_text in mappings.items():
            with self.subTest(type=input_type):
                article = self._create_test_article(article_type=input_type)
                result = self.index.prepare_mods_genre(article)

                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]['text'], expected_text)
                self.assertEqual(result[0]['authority'], 'scielo')

    # GRUPO 7: TRANSFORMAÇÃO DE FORMATO

    def test_genre_replaces_hyphens_with_spaces(self):
        """Hífens são substituídos por espaços"""
        article = self._create_test_article(article_type='product-review')
        result = self.index.prepare_mods_genre(article)

        self.assertNotIn('-', result[0]['text'])
        self.assertEqual(result[0]['text'], 'Product Review')

    def test_genre_titlecase_applied(self):
        """Title case aplicado em tipos desconhecidos"""
        article = self._create_test_article(article_type='technical-note')
        result = self.index.prepare_mods_genre(article)

        # Cada palavra começa com maiúscula
        self.assertEqual(result[0]['text'], 'Technical Note')

# Comando para execução:
# python manage.py test --keepdb article.tests.test_mods.test_genre.MODSGenreTestCase --parallel 2 -v 2
