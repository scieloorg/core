import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model

from article.models import Article
from article.search_indexes import ArticleOAIMODSIndex
from core.models import Language

User = get_user_model()


class MODSTypeOfResourceTestCase(TestCase):
    """
    Testes unitários para elemento typeOfResource MODS
    Testa mapeamento de tipos e estrutura de atributos
    """

    @classmethod
    def setUpTestData(cls):
        """Dados compartilhados entre testes para melhor performance"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

        # Criar idiomas base
        cls.lang_pt = Language.objects.create(
            code2='pt',
            name='Português',
            creator=cls.user
        )

        cls.lang_en = Language.objects.create(
            code2='en',
            name='English',
            creator=cls.user
        )

        cls.lang_es = Language.objects.create(
            code2='es',
            name='Español',
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

    def test_basic_type_of_resource_structure(self):
        """Teste: estrutura básica do typeOfResource"""
        article = self._create_test_article()

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertIsInstance(type_data, dict)
        self.assertIn('text', type_data)
        self.assertEqual(type_data['text'], 'text/digital')

    def test_type_mapping_research_article(self):
        """Teste: mapeamento research-article"""
        article = self._create_test_article(article_type='research-article')

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertEqual(type_data['text'], 'text/digital')
        self.assertIn('displayLabel', type_data)
        self.assertEqual(type_data['displayLabel'], 'Research Article')

    def test_type_mapping_all_supported_types(self):
        """Teste: mapeamento de todos os tipos suportados"""
        type_mappings = {
            'research-article': ('text/digital', 'Research Article'),
            'review-article': ('text/digital', 'Review Article'),
            'case-report': ('text/digital', 'Case Report'),
            'editorial': ('text/digital', 'Editorial'),
            'letter': ('text/digital', 'Letter'),
            'brief-report': ('text/digital', 'Brief Report'),
            'correction': ('text/digital', 'Correction'),
            'retraction': ('text/digital', 'Retraction'),
        }

        for article_type, (expected_text, expected_label) in type_mappings.items():
            with self.subTest(article_type=article_type):
                article = self._create_test_article(article_type=article_type)
                type_data = self.index.prepare_mods_type_of_resource(article)

                self.assertEqual(type_data['text'], expected_text)
                self.assertEqual(type_data['displayLabel'], expected_label)

    def test_type_mapping_unknown_type(self):
        """Teste: tipo desconhecido"""
        article = self._create_test_article(article_type='unknown-type')

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertEqual(type_data['text'], 'text/digital')
        self.assertIn('displayLabel', type_data)
        self.assertEqual(type_data['displayLabel'], 'Unknown Type')

    def test_type_mapping_none_type(self):
        """Teste: article_type None"""
        article = self._create_test_article(article_type=None)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertEqual(type_data['text'], 'text/digital')
        self.assertNotIn('displayLabel', type_data)

    def test_id_attribute_with_pid_v3(self):
        """Teste: atributo ID com pid_v3"""
        pid_v3 = 'ABC123XYZ789UNIQUE'
        article = self._create_test_article(pid_v3=pid_v3)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertIn('ID', type_data)
        self.assertEqual(type_data['ID'], pid_v3)

    def test_id_attribute_with_pid_v2_fallback(self):
        """Teste: fallback para pid_v2"""
        pid_v2 = 'S0123-45678901234567'
        article = self._create_test_article(pid_v3=None, pid_v2=pid_v2)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertIn('ID', type_data)
        self.assertEqual(type_data['ID'], pid_v2)

    def test_id_attribute_priority_v3_over_v2(self):
        """Teste: prioridade pid_v3 sobre pid_v2"""
        pid_v3 = 'NEW123UNIQUE456'
        pid_v2 = 'S0123-45678901234567'
        article = self._create_test_article(pid_v3=pid_v3, pid_v2=pid_v2)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertEqual(type_data['ID'], pid_v3)

    def test_id_attribute_no_pids(self):
        """Teste: sem PIDs"""
        article = self._create_test_article(pid_v3=None, pid_v2=None)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertNotIn('ID', type_data)

    def test_lang_attribute_single_language(self):
        """Teste: idioma único"""
        article = self._create_test_article()
        article.languages.add(self.lang_pt)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertIn('lang', type_data)
        self.assertEqual(type_data['lang'], 'pt')

    def test_lang_attribute_multiple_languages(self):
        """Teste: múltiplos idiomas usa primeiro"""
        article = self._create_test_article()
        article.languages.add(self.lang_pt, self.lang_en, self.lang_es)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertIn('lang', type_data)
        self.assertIn(type_data['lang'], ['pt', 'en', 'es'])

    def test_lang_attribute_no_languages(self):
        """Teste: sem idiomas"""
        article = self._create_test_article()

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertNotIn('lang', type_data)

    def test_lang_attribute_language_without_code(self):
        """Teste: idioma sem code2"""
        article = self._create_test_article()

        lang_without_code = Language.objects.create(
            name='Idioma sem código',
            code2=None,
            creator=self.user
        )
        article.languages.add(lang_without_code)

        type_data = self.index.prepare_mods_type_of_resource(article)

        # Não deve causar erro
        self.assertIsInstance(type_data, dict)

    def test_display_label_formatting(self):
        """Teste: formatação do displayLabel"""
        test_cases = [
            ('research-article', 'Research Article'),
            ('review-article', 'Review Article'),
            ('case-report', 'Case Report'),
            ('brief-report', 'Brief Report'),
        ]

        for article_type, expected_label in test_cases:
            with self.subTest(article_type=article_type):
                article = self._create_test_article(article_type=article_type)
                type_data = self.index.prepare_mods_type_of_resource(article)

                self.assertEqual(type_data['displayLabel'], expected_label)

    def test_complete_structure_all_attributes(self):
        """Teste: estrutura completa com todos os atributos"""
        pid_v3 = 'COMPLETE123TEST'
        article = self._create_test_article(
            pid_v3=pid_v3,
            article_type='research-article'
        )
        article.languages.add(self.lang_en)

        type_data = self.index.prepare_mods_type_of_resource(article)

        expected_fields = {
            'text': 'text/digital',
            'ID': pid_v3,
            'lang': 'en',
            'displayLabel': 'Research Article'
        }

        for field, expected_value in expected_fields.items():
            self.assertIn(field, type_data)
            self.assertEqual(type_data[field], expected_value)

    def test_minimal_structure(self):
        """Teste: estrutura mínima apenas campos obrigatórios"""
        article = self._create_test_article(
            pid_v3=None,
            pid_v2=None,
            article_type=None
        )

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertEqual(len(type_data), 1)
        self.assertIn('text', type_data)
        self.assertEqual(type_data['text'], 'text/digital')

    def test_none_values_filtering(self):
        """Teste: filtro de valores None"""
        article = self._create_test_article()

        type_data = self.index.prepare_mods_type_of_resource(article)

        for key, value in type_data.items():
            self.assertIsNotNone(value, f"Campo '{key}' não deveria ser None")

    def test_edge_case_empty_strings(self):
        """Teste: strings vazias"""
        article = self._create_test_article(
            pid_v3='',
            pid_v2='',
            article_type=''
        )

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertNotIn('ID', type_data)
        self.assertEqual(type_data['text'], 'text/digital')

    def test_case_sensitivity_article_type(self):
        """Teste: sensibilidade a maiúsculas/minúsculas"""
        article = self._create_test_article(article_type='RESEARCH-ARTICLE')

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertEqual(type_data['text'], 'text/digital')
        self.assertIn('displayLabel', type_data)
        self.assertEqual(type_data['displayLabel'], 'Research Article')

    def test_unicode_handling_in_pids(self):
        """Teste: Unicode em PIDs"""
        pid_with_unicode = 'TEST123ÃÇÉ'
        article = self._create_test_article(pid_v3=pid_with_unicode)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertEqual(type_data['ID'], pid_with_unicode)

    def test_return_type_consistency(self):
        """Teste: consistência do tipo de retorno"""
        test_cases = [
            ('minimal', lambda: self._create_test_article(pid_v3=None, article_type=None)),
            ('complete', lambda: self._create_article_with_all_data()),
        ]

        for test_name, article_creator in test_cases:
            with self.subTest(test=test_name):
                article = article_creator()

                type_data = self.index.prepare_mods_type_of_resource(article)

                self.assertIsInstance(type_data, dict)

                for key, value in type_data.items():
                    self.assertIsInstance(key, str)
                    self.assertIsInstance(value, str)

    def test_method_isolation(self):
        """Teste: método não modifica objeto"""
        original_pid = 'ORIGINAL123'
        article = self._create_test_article(pid_v3=original_pid)
        original_type = article.article_type

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertEqual(article.pid_v3, original_pid)
        self.assertEqual(article.article_type, original_type)

    def test_multiple_calls_consistency(self):
        """Teste: consistência entre múltiplas chamadas"""
        article = self._create_test_article(
            pid_v3='CONSISTENT123',
            article_type='research-article'
        )
        article.languages.add(self.lang_pt)

        result1 = self.index.prepare_mods_type_of_resource(article)
        result2 = self.index.prepare_mods_type_of_resource(article)
        result3 = self.index.prepare_mods_type_of_resource(article)

        self.assertEqual(result1, result2)
        self.assertEqual(result2, result3)

    def test_xml_serialization_readiness(self):
        """Teste: preparação para serialização XML"""
        article = self._create_test_article(
            pid_v3='XML123TEST',
            article_type='research-article'
        )
        article.languages.add(self.lang_en)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertIn('text', type_data)

        attributes = {k: v for k, v in type_data.items() if k != 'text'}
        for attr_name, attr_value in attributes.items():
            self.assertTrue(attr_name.replace('_', '').isalnum())
            self.assertIsInstance(attr_value, str)
            self.assertTrue(len(attr_value) > 0)

    def _create_article_with_all_data(self):
        """Helper para criar artigo com todos os dados"""
        article = self._create_test_article(
            pid_v3='FULL123',
            pid_v2='S0123-456789',
            article_type='research-article'
        )
        article.languages.add(self.lang_en)
        return article

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_type_of_resource.MODSTypeOfResourceTestCase --parallel 2 -v 2
