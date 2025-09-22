import uuid
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from article.models import Article
from article.search_indexes import ArticleOAIMODSIndex
from core.models import Language
from article import choices

User = get_user_model()


class MODSTypeOfResourceTestCase(TransactionTestCase):
    """
    Testes unitários focados no índice MODS para elemento typeOfResource

    Usa TransactionTestCase para evitar problemas com --keepdb
    e permite melhor limpeza entre testes
    """

    def setUp(self):
        """Configuração inicial dos testes"""
        self.user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4().hex[:8]}',
            email=f'test_{uuid.uuid4().hex[:8]}@example.com',
            password='testpass'
        )

        # Criar idiomas necessários
        self.lang_pt, _ = Language.objects.get_or_create(
            code2='pt',
            defaults={'name': 'Português', 'creator': self.user}
        )

        self.lang_en, _ = Language.objects.get_or_create(
            code2='en',
            defaults={'name': 'English', 'creator': self.user}
        )

        self.lang_es, _ = Language.objects.get_or_create(
            code2='es',
            defaults={'name': 'Español', 'creator': self.user}
        )

        self.index = ArticleOAIMODSIndex()

    def tearDown(self):
        """Limpeza após cada teste"""
        Article.objects.all().delete()
        super().tearDown()

    def _create_test_article(self, **kwargs):
        """Helper para criar artigo de teste único"""
        defaults = {
            'sps_pkg_name': f'test-{uuid.uuid4().hex[:12]}',
            'pid_v3': f'test-{uuid.uuid4().hex[:12]}',
            'article_type': 'research-article',
            'creator': self.user
        }
        defaults.update(kwargs)
        return Article.objects.create(**defaults)

    def test_basic_type_of_resource_structure(self):
        """Teste básico: estrutura do typeOfResource"""
        article = self._create_test_article()

        type_data = self.index.prepare_mods_type_of_resource(article)

        # Verificar estrutura básica
        self.assertIsInstance(type_data, dict, "Deve retornar um dicionário")
        self.assertIn('text', type_data, "Deve ter campo 'text'")
        self.assertEqual(type_data['text'], 'text/digital', "Tipo padrão deve ser 'text/digital'")

    def test_type_mapping_research_article(self):
        """Teste mapeamento: research-article"""
        article = self._create_test_article(article_type='research-article')

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertEqual(type_data['text'], 'text/digital', "research-article deve mapear para 'text/digital'")
        self.assertIn('displayLabel', type_data, "Deve ter displayLabel para research-article")
        self.assertEqual(type_data['displayLabel'], 'Research Article')

    def test_type_mapping_all_supported_types(self):
        """Teste mapeamento: todos os tipos suportados"""
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
        """Teste mapeamento: tipo desconhecido"""
        article = self._create_test_article(article_type='unknown-type')

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertEqual(type_data['text'], 'text/digital', "Tipo desconhecido deve mapear para 'text/digital'")
        # A implementação atual sempre gera displayLabel se há article_type
        self.assertIn('displayLabel', type_data, "Deve ter displayLabel para qualquer article_type")
        self.assertEqual(type_data['displayLabel'], 'Unknown Type', "DisplayLabel deve ser formatado corretamente")

    def test_type_mapping_none_type(self):
        """Teste mapeamento: article_type None"""
        article = self._create_test_article(article_type=None)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertEqual(type_data['text'], 'text/digital', "Tipo None deve mapear para 'text/digital'")
        self.assertNotIn('displayLabel', type_data, "Tipo None não deve ter displayLabel")

    def test_id_attribute_with_pid_v3(self):
        """Teste atributo ID: usando pid_v3"""
        pid_v3 = 'ABC123XYZ789UNIQUE'
        article = self._create_test_article(pid_v3=pid_v3)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertIn('ID', type_data, "Deve ter atributo ID")
        self.assertEqual(type_data['ID'], pid_v3, "ID deve usar pid_v3")

    def test_id_attribute_with_pid_v2_fallback(self):
        """Teste atributo ID: fallback para pid_v2"""
        pid_v2 = 'S0123-45678901234567'
        article = self._create_test_article(pid_v3=None, pid_v2=pid_v2)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertIn('ID', type_data, "Deve ter atributo ID")
        self.assertEqual(type_data['ID'], pid_v2, "ID deve usar pid_v2 como fallback")

    def test_id_attribute_priority_v3_over_v2(self):
        """Teste atributo ID: prioridade pid_v3 sobre pid_v2"""
        pid_v3 = 'NEW123UNIQUE456'
        pid_v2 = 'S0123-45678901234567'
        article = self._create_test_article(pid_v3=pid_v3, pid_v2=pid_v2)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertEqual(type_data['ID'], pid_v3, "Deve priorizar pid_v3 sobre pid_v2")

    def test_id_attribute_no_pids(self):
        """Teste atributo ID: sem PIDs"""
        article = self._create_test_article(pid_v3=None, pid_v2=None)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertNotIn('ID', type_data, "Não deve ter ID sem PIDs")

    def test_lang_attribute_single_language(self):
        """Teste atributo lang: idioma único"""
        article = self._create_test_article()
        article.languages.add(self.lang_pt)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertIn('lang', type_data, "Deve ter atributo lang")
        self.assertEqual(type_data['lang'], 'pt', "Lang deve usar code2 do idioma")

    def test_lang_attribute_multiple_languages(self):
        """Teste atributo lang: múltiplos idiomas (usa primeiro)"""
        article = self._create_test_article()
        article.languages.add(self.lang_pt, self.lang_en, self.lang_es)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertIn('lang', type_data, "Deve ter atributo lang")
        # Deve usar o primeiro idioma (order by pode variar)
        self.assertIn(type_data['lang'], ['pt', 'en', 'es'], "Deve usar um dos idiomas")

    def test_lang_attribute_no_languages(self):
        """Teste atributo lang: sem idiomas"""
        article = self._create_test_article()

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertNotIn('lang', type_data, "Não deve ter lang sem idiomas")

    def test_lang_attribute_exception_handling(self):
        """Teste atributo lang: tratamento de exceções"""
        article = self._create_test_article()

        # Simular cenário onde não há idiomas para testar o try/except
        # O código já trata naturalmente quando não há idiomas relacionados
        type_data = self.index.prepare_mods_type_of_resource(article)

        # Deve continuar funcionando mesmo sem idiomas
        self.assertIsInstance(type_data, dict)
        self.assertNotIn('lang', type_data, "Não deve ter lang quando não há idiomas")

        # Teste adicional: criar idioma sem code2 (cenário de erro potencial)
        lang_without_code = Language.objects.create(
            name='Idioma sem código',
            creator=self.user
            # code2 será None por padrão
        )
        article.languages.add(lang_without_code)

        type_data_with_invalid_lang = self.index.prepare_mods_type_of_resource(article)

        # Deve continuar funcionando e não incluir lang com code2 None
        self.assertIsInstance(type_data_with_invalid_lang, dict)
        # O comportamento depende da implementação: pode ou não ter 'lang'
        # mas não deve causar erro

    def test_display_label_consistency(self):
        """Teste displayLabel: consistência entre tipos"""
        test_cases = [
            ('research-article', 'Research Article'),
            ('review-article', 'Review Article'),
            ('case-report', 'Case Report'),
            ('editorial', 'Editorial'),
            ('letter', 'Letter'),
            ('brief-report', 'Brief Report'),
            ('correction', 'Correction'),
            ('retraction', 'Retraction'),
        ]

        for article_type, expected_label in test_cases:
            with self.subTest(article_type=article_type):
                article = self._create_test_article(article_type=article_type)
                type_data = self.index.prepare_mods_type_of_resource(article)

                self.assertEqual(type_data['displayLabel'], expected_label,
                                 f"displayLabel incorreto para {article_type}")

    def test_complete_structure_research_article(self):
        """Teste estrutura completa: research-article com todos os atributos"""
        pid_v3 = 'COMPLETE123TEST'
        article = self._create_test_article(
            pid_v3=pid_v3,
            article_type='research-article'
        )
        article.languages.add(self.lang_en)

        type_data = self.index.prepare_mods_type_of_resource(article)

        # Verificar todos os campos esperados
        expected_fields = {
            'text': 'text/digital',
            'ID': pid_v3,
            'lang': 'en',
            'displayLabel': 'Research Article'
        }

        for field, expected_value in expected_fields.items():
            self.assertIn(field, type_data, f"Campo {field} deve estar presente")
            self.assertEqual(type_data[field], expected_value,
                             f"Valor incorreto para {field}")

    def test_minimal_structure(self):
        """Teste estrutura mínima: apenas campos obrigatórios"""
        article = self._create_test_article(
            pid_v3=None,
            pid_v2=None,
            article_type=None
        )

        type_data = self.index.prepare_mods_type_of_resource(article)

        # Apenas o campo text deve estar presente
        self.assertEqual(len(type_data), 1, "Deve ter apenas 1 campo")
        self.assertIn('text', type_data, "Campo text deve estar presente")
        self.assertEqual(type_data['text'], 'text/digital', "Valor padrão deve ser 'text/digital'")

    def test_none_values_filtering(self):
        """Teste filtro de valores None: garantir que não aparecem no resultado"""
        article = self._create_test_article()

        type_data = self.index.prepare_mods_type_of_resource(article)

        # Verificar que não há valores None
        for key, value in type_data.items():
            self.assertIsNotNone(value, f"Campo '{key}' não deveria ser None")

    def test_edge_case_empty_strings(self):
        """Teste casos extremos: strings vazias"""
        article = self._create_test_article(
            pid_v3='',  # String vazia
            pid_v2='',
            article_type=''
        )

        type_data = self.index.prepare_mods_type_of_resource(article)

        # Strings vazias devem ser tratadas como None para PIDs
        self.assertNotIn('ID', type_data, "String vazia não deve gerar ID")
        self.assertEqual(type_data['text'], 'text/digital', "String vazia deve usar valor padrão")
        # String vazia deve gerar displayLabel vazio após replace e title
        self.assertIn('displayLabel', type_data, "Deve ter displayLabel mesmo com string vazia")
        self.assertEqual(type_data['displayLabel'], '', "DisplayLabel de string vazia deve ser string vazia")

    def test_case_sensitivity_article_type(self):
        """Teste sensibilidade a maiúsculas/minúsculas no article_type"""
        # Tipos em maiúsculas não devem ser reconhecidos
        article = self._create_test_article(article_type='RESEARCH-ARTICLE')

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertEqual(type_data['text'], 'text/digital')
        # Deve ter displayLabel porque a implementação atual faz replace e title
        self.assertIn('displayLabel', type_data, "Deve ter displayLabel mesmo em maiúscula")
        self.assertEqual(type_data['displayLabel'], 'Research Article')

    def test_unicode_handling(self):
        """Teste tratamento de Unicode em PIDs"""
        pid_with_unicode = 'TEST123ÃÇÉ'
        article = self._create_test_article(pid_v3=pid_with_unicode)

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertEqual(type_data['ID'], pid_with_unicode, "Unicode deve ser preservado")

    def test_return_type_consistency(self):
        """Teste consistência do tipo de retorno"""
        article = self._create_test_article()

        type_data = self.index.prepare_mods_type_of_resource(article)

        self.assertIsInstance(type_data, dict, "Deve sempre retornar dict")

        # Todos os valores devem ser strings
        for key, value in type_data.items():
            self.assertIsInstance(key, str, f"Chave '{key}' deve ser string")
            self.assertIsInstance(value, str, f"Valor de '{key}' deve ser string")

    def test_method_isolation(self):
        """Teste isolamento do método: não deve modificar o objeto"""
        original_pid = 'ORIGINAL123'
        article = self._create_test_article(pid_v3=original_pid)
        original_type = article.article_type

        # Chamar o método
        type_data = self.index.prepare_mods_type_of_resource(article)

        # Verificar que o objeto não foi modificado
        self.assertEqual(article.pid_v3, original_pid, "pid_v3 não deve ser modificado")
        self.assertEqual(article.article_type, original_type, "article_type não deve ser modificado")

    def test_multiple_calls_consistency(self):
        """Teste consistência entre múltiplas chamadas"""
        article = self._create_test_article(
            pid_v3='CONSISTENT123',
            article_type='research-article'
        )
        article.languages.add(self.lang_pt)

        # Múltiplas chamadas
        result1 = self.index.prepare_mods_type_of_resource(article)
        result2 = self.index.prepare_mods_type_of_resource(article)
        result3 = self.index.prepare_mods_type_of_resource(article)

        # Resultados devem ser idênticos
        self.assertEqual(result1, result2, "Resultados devem ser consistentes")
        self.assertEqual(result2, result3, "Resultados devem ser consistentes")

    def test_xml_serialization_readiness(self):
        """Teste preparação para serialização XML: estrutura adequada"""
        article = self._create_test_article(
            pid_v3='XML123TEST',
            article_type='research-article'
        )
        article.languages.add(self.lang_en)

        type_data = self.index.prepare_mods_type_of_resource(article)

        # Simular serialização XML básica
        # O campo 'text' deve ser o conteúdo do elemento
        self.assertIn('text', type_data, "Deve ter conteúdo do elemento")

        # Outros campos devem ser atributos XML
        attributes = {k: v for k, v in type_data.items() if k != 'text'}
        for attr_name, attr_value in attributes.items():
            # Nomes de atributos válidos para XML
            self.assertTrue(attr_name.replace('_', '').isalnum(),
                            f"Atributo '{attr_name}' deve ser válido para XML")
            # Valores devem ser strings não vazias
            self.assertIsInstance(attr_value, str,
                                  f"Valor do atributo '{attr_name}' deve ser string")
            self.assertTrue(len(attr_value) > 0,
                            f"Valor do atributo '{attr_name}' não deve estar vazio")

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_type_of_resource.MODSTypeOfResourceTestCase -v 2
