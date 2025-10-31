import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from article.models import Article, DocumentTitle
from article.search_indexes import ArticleOAIMODSIndex
from core.models import Language

User = get_user_model()


class MODSTitleInfoTestCase(TestCase):
    """
    Testes unitários otimizados para elemento titleInfo MODS
    Testa estrutura e funcionalidades de títulos no ecossistema SciELO
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

    def _create_test_title(self, plain_text, language=None):
        """Helper para criar DocumentTitle de teste"""
        return DocumentTitle.objects.create(
            plain_text=plain_text,
            language=language,
            creator=self.user
        )

    def test_title_info_no_titles(self):
        """Teste: artigo sem títulos"""
        article = self._create_test_article()

        mods_titles = self.index.prepare_mods_title_info(article)

        self.assertEqual(len(mods_titles), 0)

    def test_title_info_single_title_basic(self):
        """Teste: título único com idioma"""
        article = self._create_test_article()

        title = self._create_test_title(
            "Análise de Dados em Ciência da Computação",
            self.lang_pt
        )
        article.titles.add(title)

        mods_titles = self.index.prepare_mods_title_info(article)

        self.assertEqual(len(mods_titles), 1)

        mods_title = mods_titles[0]
        self.assertIn('title', mods_title)
        self.assertEqual(mods_title['title'], "Análise de Dados em Ciência da Computação")

        # Verificar idioma se presente
        if 'lang' in mods_title:
            self.assertEqual(mods_title['lang'], 'pt')

    def test_title_info_multiple_languages(self):
        """Teste: múltiplos títulos em idiomas diferentes"""
        article = self._create_test_article()

        titles_data = [
            ("Inteligência Artificial na Medicina: Revisão Sistemática", self.lang_pt, 'pt'),
            ("Artificial Intelligence in Medicine: A Systematic Review", self.lang_en, 'en'),
            ("Inteligencia Artificial en Medicina: Una Revisión Sistemática", self.lang_es, 'es'),
        ]

        # Criar títulos
        for title_text, language, expected_lang in titles_data:
            title = self._create_test_title(title_text, language)
            article.titles.add(title)

        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 3)

        # Verificar estrutura básica
        for mods_title in mods_titles:
            self.assertIn('title', mods_title)
            self.assertTrue(len(mods_title['title']) > 0)

        # Verificar idiomas se presentes
        mods_langs = {title.get('lang') for title in mods_titles if 'lang' in title}
        expected_langs = {'pt', 'en', 'es'}
        self.assertEqual(mods_langs, expected_langs)

        # Verificar conteúdo específico
        mods_texts = {title['title'] for title in mods_titles}
        expected_keywords = [
            "Inteligência Artificial na Medicina",
            "Artificial Intelligence in Medicine",
            "Inteligencia Artificial en Medicina"
        ]

        for keyword in expected_keywords:
            self.assertTrue(
                any(keyword in text for text in mods_texts),
                f"Keyword '{keyword}' não encontrada nos títulos"
            )

    def test_title_info_without_language(self):
        """Teste: título sem idioma especificado"""
        article = self._create_test_article()

        title = self._create_test_title(
            "Título sem idioma especificado para teste do índice",
            language=None
        )
        article.titles.add(title)

        mods_titles = self.index.prepare_mods_title_info(article)

        self.assertEqual(len(mods_titles), 1)

        mods_title = mods_titles[0]
        self.assertIn('title', mods_title)
        self.assertEqual(mods_title['title'], "Título sem idioma especificado para teste do índice")

        # Verificar que 'lang' não está presente ou é tratado adequadamente
        if 'lang' in mods_title:
            # Se presente, deve ser None ou código válido
            self.assertTrue(
                mods_title['lang'] is None or isinstance(mods_title['lang'], str)
            )

    def test_title_info_complex_content_variations(self):
        """Teste: diferentes tipos de conteúdo de título"""
        article = self._create_test_article()

        content_test_cases = [
            ("Machine Learning Applications in Healthcare: A Systematic Review", self.lang_en),
            ("COVID-19 & SARS-CoV-2: Análise Genômica (2020-2023) — Revisão", self.lang_pt),
            ("Título Complexo: Análise & Síntese — Estudo (2024)", self.lang_pt),
        ]

        # Criar títulos com conteúdo variado
        for title_text, language in content_test_cases:
            title = self._create_test_title(title_text, language)
            article.titles.add(title)

        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 3)

        # Verificar preservação de conteúdo complexo
        mods_texts = [title['title'] for title in mods_titles]

        # Verificar elementos específicos
        complex_elements = [
            ("Machine Learning", "Termo técnico preservado"),
            ("COVID-19", "Números com hífen preservados"),
            ("&", "Símbolos especiais preservados"),
            ("—", "Em dash preservado"),
            ("(2020-2023)", "Intervalos de anos preservados"),
            ("Análise", "Acentos preservados"),
        ]

        for element, description in complex_elements:
            found = any(element in text for text in mods_texts)
            self.assertTrue(found, f"{description}: '{element}' não encontrado")

    def test_title_info_edge_cases_handling(self):
        """Teste: casos extremos de títulos"""
        article = self._create_test_article()

        edge_cases = [
            ("", "empty_title"),
            ("   \n\t   ", "whitespace_only"),
            ("Single", "single_word"),
            ("A" * 500, "very_long_title"),
        ]

        # Criar títulos com casos extremos
        for title_text, case_desc in edge_cases:
            title = self._create_test_title(title_text, self.lang_pt)
            article.titles.add(title)

        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 4)

        # Verificar que todos foram preservados
        mods_texts = [title['title'] for title in mods_titles]

        for title_text, case_desc in edge_cases:
            with self.subTest(case=case_desc):
                self.assertIn(title_text, mods_texts, f"Caso '{case_desc}' não preservado")

    def test_title_info_none_values_filtering(self):
        """Teste: filtro de valores None na estrutura MODS"""
        article = self._create_test_article()

        # Título sem idioma para testar filtro de None
        title = self._create_test_title(
            "Título para teste de filtro de valores None",
            language=None
        )
        article.titles.add(title)

        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 1)

        mods_title = mods_titles[0]

        # Verificar que campos None não estão presentes (se filtrados)
        # ou são tratados adequadamente
        for key, value in mods_title.items():
            if value is not None:
                self.assertIsInstance(value, (str, int, float, bool, list, dict))

        # Campo 'title' deve estar sempre presente
        self.assertIn('title', mods_title)

    def test_title_info_structure_consistency(self):
        """Teste: consistência da estrutura titleInfo"""
        article = self._create_test_article()

        # Diferentes configurações de títulos
        test_configurations = [
            ("Título com idioma", self.lang_pt),
            ("Title without language", None),
            ("Título especial: teste & validação", self.lang_pt),
        ]

        for title_text, language in test_configurations:
            title = self._create_test_title(title_text, language)
            article.titles.add(title)

        mods_titles = self.index.prepare_mods_title_info(article)

        # Validar estrutura de cada título
        for i, mods_title in enumerate(mods_titles):
            with self.subTest(title_index=i):
                # Verificar estrutura básica
                self.assertIsInstance(mods_title, dict)
                self.assertIn('title', mods_title)
                self.assertIsInstance(mods_title['title'], str)

                # Verificar campos opcionais
                if 'lang' in mods_title:
                    lang_value = mods_title['lang']
                    self.assertTrue(
                        lang_value is None or isinstance(lang_value, str),
                        f"Campo 'lang' deve ser None ou string, foi: {type(lang_value)}"
                    )

                # Verificar outros campos possíveis (baseado na implementação real)
                for key, value in mods_title.items():
                    self.assertIsInstance(key, str, f"Chave deve ser string: {key}")

    def test_title_info_mixed_scenario_complete(self):
        """Teste: cenário completo com títulos variados"""
        article = self._create_test_article()

        # Cenário misto realista
        mixed_titles = [
            ("Título normal em português", self.lang_pt),
            ("Title without language specification", None),
            ("Título Complexo: Análise & Síntese — Estudo (2024)", self.lang_pt),
            ("   ", self.lang_en),  # Título com apenas espaços
            ("", None),  # Título vazio
        ]

        for title_text, language in mixed_titles:
            title = self._create_test_title(title_text, language)
            article.titles.add(title)

        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 5)

        # Verificar estrutura básica de todos
        for mods_title in mods_titles:
            self.assertIn('title', mods_title)

        # Contar títulos com/sem idioma
        with_lang = [title for title in mods_titles
                     if 'lang' in title and title['lang'] is not None]

        # Verificar que temos títulos com e sem idioma
        self.assertGreater(len(with_lang), 0)

        # Verificar conteúdos específicos
        mods_texts = [title['title'] for title in mods_titles]
        expected_contents = [
            "Título normal em português",
            "Title without language specification",
            "Complexo",  # Parte do título complexo
            "   ",  # Espaços preservados
            "",  # String vazia preservada
        ]

        for content in expected_contents:
            found = any(content in text for text in mods_texts)
            self.assertTrue(found, f"Conteúdo esperado não encontrado: '{content}'")

    def test_title_info_document_title_model_validation(self):
        """Teste: validação do modelo DocumentTitle"""
        article = self._create_test_article()

        # Criar título para validar modelo
        title = self._create_test_title(
            "Título de teste para validação do modelo",
            self.lang_pt
        )
        article.titles.add(title)

        # Validações do modelo
        self.assertIsNotNone(title.id)
        self.assertEqual(title.language, self.lang_pt)
        self.assertEqual(title.creator, self.user)
        self.assertIn("teste", title.plain_text)

        # Verificar relacionamento ManyToMany
        self.assertEqual(article.titles.count(), 1)
        self.assertIn(title, article.titles.all())

        # Verificar mapeamento MODS
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 1)
        self.assertIn("teste", mods_titles[0]['title'])

    def test_title_info_return_type_consistency(self):
        """Teste: consistência do tipo de retorno"""
        consistency_tests = [
            ('no_titles', lambda: self._create_test_article()),
            ('single_title', lambda: self._create_article_with_title("Single Title")),
            ('multiple_titles', lambda: self._create_article_with_multiple_titles()),
        ]

        for test_name, article_creator in consistency_tests:
            with self.subTest(test=test_name):
                article = article_creator()

                mods_titles = self.index.prepare_mods_title_info(article)

                # Sempre deve retornar lista
                self.assertIsInstance(mods_titles, list)

                # Se não vazio, verificar estrutura
                for title_info in mods_titles:
                    self.assertIsInstance(title_info, dict)
                    self.assertIn('title', title_info)
                    self.assertIsInstance(title_info['title'], str)

    def _create_article_with_title(self, title_text):
        """Helper para criar artigo com título único"""
        article = self._create_test_article()
        title = self._create_test_title(title_text, self.lang_pt)
        article.titles.add(title)
        return article

    def _create_article_with_multiple_titles(self):
        """Helper para criar artigo com múltiplos títulos"""
        article = self._create_test_article()

        titles = [
            ("Primeiro Título", self.lang_pt),
            ("Second Title", self.lang_en),
        ]

        for title_text, language in titles:
            title = self._create_test_title(title_text, language)
            article.titles.add(title)

        return article

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_title_info.MODSTitleInfoTestCase --parallel 2 -v 2
