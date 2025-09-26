import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from article.models import Article
from article.search_indexes import ArticleOAIMODSIndex
from core.models import Language

User = get_user_model()


class MODSLanguageTestCase(TestCase):
    """
    Testes unitários otimizados para elemento language MODS
    Testa estrutura e funcionalidades de idiomas no ecossistema SciELO
    """

    @classmethod
    def setUpTestData(cls):
        """Dados compartilhados entre testes para melhor performance"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

        # Criar idiomas base uma vez
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

        cls.lang_fr = Language.objects.create(
            code2='fr',
            name='Français',
            creator=cls.user
        )

        cls.lang_zh = Language.objects.create(
            code2='zh',
            name='中文',
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

    def _create_test_language(self, **kwargs):
        """Helper para criar idioma de teste"""
        defaults = {
            'creator': self.user
        }
        defaults.update(kwargs)
        return Language.objects.create(**defaults)

    def test_language_no_languages(self):
        """Teste: artigo sem idiomas"""
        article = self._create_test_article()

        languages = self.index.prepare_mods_language(article)

        self.assertIsInstance(languages, list)
        self.assertEqual(len(languages), 0)

    def test_language_basic_structure(self):
        """Teste: estrutura básica do language"""
        article = self._create_test_article()
        article.languages.add(self.lang_pt)

        languages = self.index.prepare_mods_language(article)

        # Verificar estrutura básica
        self.assertIsInstance(languages, list)
        self.assertEqual(len(languages), 1)

        lang_data = languages[0]
        self.assertIsInstance(lang_data, dict)
        self.assertIn("languageTerm", lang_data)
        self.assertIsInstance(lang_data["languageTerm"], list)
        self.assertGreater(len(lang_data["languageTerm"]), 0)

    def test_language_single_with_code_and_text(self):
        """Teste: idioma único com código e texto"""
        article = self._create_test_article()
        article.languages.add(self.lang_en)

        languages = self.index.prepare_mods_language(article)

        lang_data = languages[0]
        terms = lang_data["languageTerm"]

        # Verificar se há termo com código
        code_terms = [t for t in terms if t.get("type") == "code"]
        self.assertGreater(len(code_terms), 0)

        code_term = code_terms[0]
        self.assertIn("authority", code_term)
        self.assertIn("text", code_term)
        self.assertTrue(code_term["text"].strip())

    def test_language_primary_usage_assignment(self):
        """Teste: atributo usage='primary' no primeiro idioma"""
        article = self._create_test_article()
        article.languages.add(self.lang_pt, self.lang_en, self.lang_es)

        languages = self.index.prepare_mods_language(article)

        # Primeiro idioma deve ter usage="primary"
        first_lang = languages[0]
        self.assertIn("usage", first_lang)
        self.assertEqual(first_lang["usage"], "primary")

        # Outros idiomas não devem ter usage
        for lang_data in languages[1:]:
            self.assertNotIn("usage", lang_data)

        # Apenas um idioma deve ter usage="primary"
        usage_count = sum(1 for lang in languages if lang.get("usage") == "primary")
        self.assertEqual(usage_count, 1)

    def test_language_multiple_languages_structure(self):
        """Teste: múltiplos idiomas - estrutura e ordem"""
        article = self._create_test_article()
        article.languages.add(self.lang_pt, self.lang_en, self.lang_es, self.lang_fr)

        languages = self.index.prepare_mods_language(article)

        self.assertEqual(len(languages), 4)

        # Todos devem ter languageTerm válido
        for lang_data in languages:
            self.assertIn("languageTerm", lang_data)
            self.assertIsInstance(lang_data["languageTerm"], list)
            self.assertGreater(len(lang_data["languageTerm"]), 0)

            # Verificar estrutura dos termos
            for term in lang_data["languageTerm"]:
                self.assertIsInstance(term, dict)
                self.assertIn("type", term)
                self.assertIn("text", term)
                self.assertIn(term["type"], ["code", "text"])

    def test_language_terms_structure_validation(self):
        """Teste: estrutura dos languageTerms"""
        test_languages = [self.lang_fr, self.lang_zh, self.lang_en]

        for test_lang in test_languages:
            with self.subTest(language=test_lang.code2):
                article = self._create_test_article()
                article.languages.add(test_lang)

                languages = self.index.prepare_mods_language(article)

                lang_data = languages[0]
                terms = lang_data["languageTerm"]

                # Verificar tipos presentes
                types_present = {term["type"] for term in terms}

                if test_lang.code2 and test_lang.name:
                    self.assertIn("code", types_present)
                    self.assertIn("text", types_present)

                # Verificar conteúdo dos termos
                for term in terms:
                    self.assertTrue(term["text"].strip())
                    if term["type"] == "code":
                        self.assertIn("authority", term)

    def test_language_script_term_latin_languages(self):
        """Teste: scriptTerm para idiomas com escrita latina"""
        latin_languages = [self.lang_en, self.lang_pt, self.lang_es, self.lang_fr]

        for lang in latin_languages:
            with self.subTest(language=lang.code2):
                article = self._create_test_article()
                article.languages.add(lang)

                languages = self.index.prepare_mods_language(article)
                lang_data = languages[0]

                # Verificar se tem scriptTerm para idiomas latinos
                if "scriptTerm" in lang_data:
                    script_terms = lang_data["scriptTerm"]
                    self.assertIsInstance(script_terms, list)

                    if script_terms:
                        script_term = script_terms[0]
                        self.assertEqual(script_term["type"], "code")
                        self.assertEqual(script_term["authority"], "iso15924")
                        self.assertEqual(script_term["text"], "Latn")

    def test_language_edge_cases_handling(self):
        """Teste: casos extremos de idiomas"""
        edge_cases = [
            # (code2, name, description)
            (None, 'Idioma Teste', 'sem_codigo'),
            ('de', None, 'sem_nome'),
            ('', '   ', 'campos_vazios'),
            ('zh', '中文', 'caracteres_especiais'),
        ]

        for code2, name, case_desc in edge_cases:
            with self.subTest(case=case_desc):
                lang_edge = self._create_test_language(
                    code2=code2,
                    name=name
                )

                article = self._create_test_article()
                article.languages.add(lang_edge)

                languages = self.index.prepare_mods_language(article)

                # Deve sempre retornar lista válida
                self.assertIsInstance(languages, list)

                # Se retorna dados, deve ter estrutura válida
                if languages:
                    lang_data = languages[0]
                    if "languageTerm" in lang_data:
                        for term in lang_data["languageTerm"]:
                            # Texto não deve estar vazio após strip
                            if "text" in term:
                                self.assertTrue(
                                    term["text"].strip() or term.get("type") == "code",
                                    f"Texto inválido para caso {case_desc}"
                                )

    def test_language_iso_mapping_consistency(self):
        """Teste: consistência do mapeamento ISO"""
        iso_test_cases = [
            (self.lang_pt, "pt"),
            (self.lang_en, "en"),
            (self.lang_es, "es"),
            (self.lang_fr, "fr"),
        ]

        for lang, expected_code in iso_test_cases:
            with self.subTest(language=expected_code):
                article = self._create_test_article()
                article.languages.add(lang)

                languages = self.index.prepare_mods_language(article)
                lang_data = languages[0]
                terms = lang_data["languageTerm"]

                # Encontrar termo código
                code_terms = [t for t in terms if t.get("type") == "code"]
                self.assertGreater(len(code_terms), 0)

                code_term = code_terms[0]
                self.assertIn("authority", code_term)

                authority = code_term["authority"]
                self.assertIn(authority, ["iso639-1", "iso639-2b"])

                # Verificar comprimento do código
                code_text = code_term["text"]
                if authority == "iso639-1":
                    self.assertEqual(len(code_text), 2)
                elif authority == "iso639-2b":
                    self.assertEqual(len(code_text), 3)

    def test_language_return_type_consistency(self):
        """Teste: consistência do tipo de retorno"""
        consistency_tests = [
            ("empty", []),
            ("single", [self.lang_pt]),
            ("multiple", [self.lang_pt, self.lang_en, self.lang_es]),
        ]

        for test_name, languages_to_add in consistency_tests:
            with self.subTest(test=test_name):
                article = self._create_test_article()

                for lang in languages_to_add:
                    article.languages.add(lang)

                languages = self.index.prepare_mods_language(article)

                # Sempre deve retornar lista
                self.assertIsInstance(languages, list)

                # Verificar estrutura interna
                for lang_data in languages:
                    self.assertIsInstance(lang_data, dict)

                    if "languageTerm" in lang_data:
                        self.assertIsInstance(lang_data["languageTerm"], list)

                        for term in lang_data["languageTerm"]:
                            self.assertIsInstance(term, dict)
                            self.assertIsInstance(term.get("type", ""), str)
                            self.assertIsInstance(term.get("text", ""), str)

    def test_language_special_characters_handling(self):
        """Teste: tratamento de caracteres especiais"""
        special_cases = [
            ('zh', '中文'),
            ('ar', 'العربية'),
            ('ru', 'Русский'),
            ('ja', '日本語'),
        ]

        for code, name in special_cases:
            with self.subTest(language=code):
                lang_special = self._create_test_language(
                    code2=code,
                    name=name
                )

                article = self._create_test_article()
                article.languages.add(lang_special)

                languages = self.index.prepare_mods_language(article)

                if languages:
                    lang_data = languages[0]
                    terms = lang_data["languageTerm"]

                    # Verificar se preserva caracteres Unicode
                    text_terms = [t for t in terms if t.get("type") == "text"]
                    if text_terms:
                        text_term = text_terms[0]
                        self.assertEqual(text_term["text"], name)

    def test_language_priority_and_ordering(self):
        """Teste: prioridade e ordenação de idiomas"""
        article = self._create_test_article()

        # Adicionar idiomas em ordem específica
        languages_order = [self.lang_es, self.lang_pt, self.lang_en]
        for lang in languages_order:
            article.languages.add(lang)

        languages = self.index.prepare_mods_language(article)

        # Primeiro idioma sempre tem usage="primary"
        self.assertEqual(languages[0]["usage"], "primary")

        # Outros não têm usage
        for lang_data in languages[1:]:
            self.assertNotIn("usage", lang_data)

        # Verificar que todos estão presentes
        self.assertEqual(len(languages), 3)

    def test_language_mixed_valid_invalid_scenario(self):
        """Teste: cenário misto com idiomas válidos e inválidos"""
        # Criar idioma com problemas
        lang_problematic = self._create_test_language(
            code2='xx',  # Código não padrão
            name=''  # Nome vazio
        )

        article = self._create_test_article()
        article.languages.add(self.lang_pt, lang_problematic, self.lang_en)

        languages = self.index.prepare_mods_language(article)

        # Deve processar sem erros
        self.assertIsInstance(languages, list)

        # Deve ter processado pelo menos os idiomas válidos
        valid_languages = [lang for lang in languages if lang.get("languageTerm")]
        self.assertGreaterEqual(len(valid_languages), 2)

        # Primeiro idioma deve ter usage="primary"
        if languages:
            primary_count = sum(1 for lang in languages if lang.get("usage") == "primary")
            self.assertEqual(primary_count, 1)

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_mods_language.MODSLanguageTestCase --parallel 2 -v 2
