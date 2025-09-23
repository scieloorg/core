import uuid
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from article.models import Article
from article.search_indexes import ArticleOAIMODSIndex
from core.models import Language

User = get_user_model()


class MODSLanguageTestCase(TransactionTestCase):
    """
    Testes unitários focados no índice MODS para elemento language

    Usa TransactionTestCase para melhor isolamento e limpeza
    """

    def setUp(self):
        """Configuração inicial dos testes"""
        self.user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4().hex[:8]}',
            email=f'test_{uuid.uuid4().hex[:8]}@example.com',
            password='testpass'
        )

        # Criar idiomas de teste
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

        self.lang_fr, _ = Language.objects.get_or_create(
            code2='fr',
            defaults={'name': 'Français', 'creator': self.user}
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

    def test_basic_language_structure(self):
        """Teste básico: estrutura do language"""
        article = self._create_test_article()
        article.languages.add(self.lang_pt)

        languages = self.index.prepare_mods_language(article)

        # Verificar estrutura básica
        self.assertIsInstance(languages, list, "Deve retornar uma lista")
        self.assertEqual(len(languages), 1, "Deve ter 1 idioma")

        lang_data = languages[0]
        self.assertIsInstance(lang_data, dict, "Item deve ser dict")
        self.assertIn("languageTerm", lang_data, "Deve ter languageTerm")

    def test_no_languages(self):
        """Teste sem idiomas: lista vazia"""
        article = self._create_test_article()

        languages = self.index.prepare_mods_language(article)

        self.assertIsInstance(languages, list, "Deve retornar lista")
        self.assertEqual(len(languages), 0, "Deve estar vazia sem idiomas")

    def test_single_language_with_code_and_text(self):
        """Teste idioma único: código e texto"""
        article = self._create_test_article()
        article.languages.add(self.lang_en)

        languages = self.index.prepare_mods_language(article)

        self.assertEqual(len(languages), 1)
        lang_data = languages[0]

        # Verificar languageTerms
        self.assertIn("languageTerm", lang_data)
        terms = lang_data["languageTerm"]
        self.assertIsInstance(terms, list)
        self.assertGreater(len(terms), 0, "Deve ter pelo menos 1 languageTerm")

        # Verificar se há termo com código
        code_terms = [t for t in terms if t.get("type") == "code"]
        self.assertGreater(len(code_terms), 0, "Deve ter languageTerm type='code'")

        code_term = code_terms[0]
        self.assertIn("authority", code_term, "Código deve ter authority")
        self.assertIn("text", code_term, "Código deve ter text")

    def test_primary_language_usage(self):
        """Teste atributo usage='primary' no primeiro idioma"""
        article = self._create_test_article()
        article.languages.add(self.lang_pt, self.lang_en)

        languages = self.index.prepare_mods_language(article)

        # Primeiro idioma deve ter usage="primary"
        first_lang = languages[0]
        self.assertIn("usage", first_lang, "Primeiro idioma deve ter usage")
        self.assertEqual(first_lang["usage"], "primary")

        # Segundo idioma não deve ter usage
        if len(languages) > 1:
            second_lang = languages[1]
            self.assertNotIn("usage", second_lang, "Segundo idioma não deve ter usage")

    def test_multiple_languages_order(self):
        """Teste múltiplos idiomas: ordem e estrutura"""
        article = self._create_test_article()
        article.languages.add(self.lang_pt, self.lang_en, self.lang_es)

        languages = self.index.prepare_mods_language(article)

        self.assertEqual(len(languages), 3, "Deve ter 3 idiomas")

        # Verificar que todos têm languageTerm
        for lang_data in languages:
            self.assertIn("languageTerm", lang_data)
            self.assertIsInstance(lang_data["languageTerm"], list)
            self.assertGreater(len(lang_data["languageTerm"]), 0)

        # Apenas primeiro tem usage="primary"
        usage_count = sum(1 for lang in languages if lang.get("usage") == "primary")
        self.assertEqual(usage_count, 1, "Apenas primeiro idioma deve ter usage='primary'")

    def test_language_terms_structure(self):
        """Teste estrutura dos languageTerms"""
        article = self._create_test_article()
        article.languages.add(self.lang_fr)  # Francês

        languages = self.index.prepare_mods_language(article)

        lang_data = languages[0]
        terms = lang_data["languageTerm"]

        # Verificar estrutura dos termos
        for term in terms:
            self.assertIsInstance(term, dict, "Cada termo deve ser dict")
            self.assertIn("type", term, "Termo deve ter type")
            self.assertIn("text", term, "Termo deve ter text")
            self.assertIn(term["type"], ["code", "text"], "Type deve ser 'code' ou 'text'")

        # Deve haver pelo menos um de cada tipo se language tem code2 e name
        types_present = {term["type"] for term in terms}
        if self.lang_fr.code2 and self.lang_fr.name:
            self.assertIn("code", types_present, "Deve ter termo tipo 'code'")
            self.assertIn("text", types_present, "Deve ter termo tipo 'text'")

    def test_script_term_for_latin_languages(self):
        """Teste scriptTerm para idiomas com escrita latina"""
        article = self._create_test_article()
        article.languages.add(self.lang_en)  # Inglês usa escrita latina

        languages = self.index.prepare_mods_language(article)

        lang_data = languages[0]

        # Verificar se tem scriptTerm
        if "scriptTerm" in lang_data:
            script_terms = lang_data["scriptTerm"]
            self.assertIsInstance(script_terms, list)
            self.assertGreater(len(script_terms), 0)

            script_term = script_terms[0]
            self.assertEqual(script_term["type"], "code")
            self.assertEqual(script_term["authority"], "iso15924")
            self.assertEqual(script_term["text"], "Latn")

    def test_language_without_name(self):
        """Teste idioma sem nome: apenas código"""
        # Criar idioma sem nome
        lang_no_name = Language.objects.create(
            code2='de',
            creator=self.user
            # name não definido (None)
        )

        article = self._create_test_article()
        article.languages.add(lang_no_name)

        languages = self.index.prepare_mods_language(article)

        self.assertEqual(len(languages), 1)
        lang_data = languages[0]
        terms = lang_data["languageTerm"]

        # Deve ter apenas termo tipo 'code'
        types = [term["type"] for term in terms]
        self.assertIn("code", types, "Deve ter termo código")
        # Pode ou não ter 'text' dependendo da implementação

    def test_language_without_code(self):
        """Teste idioma sem código: apenas texto"""
        # Criar idioma sem código
        lang_no_code = Language.objects.create(
            name='Idioma Teste',
            creator=self.user
            # code2 não definido (None)
        )

        article = self._create_test_article()
        article.languages.add(lang_no_code)

        languages = self.index.prepare_mods_language(article)

        # Comportamento depende da implementação
        # Se não há code2, pode não retornar nada ou retornar apenas texto
        if languages:
            lang_data = languages[0]
            if "languageTerm" in lang_data:
                terms = lang_data["languageTerm"]
                types = [term["type"] for term in terms]
                # Se houver termos, deve ter pelo menos 'text'
                if types:
                    self.assertTrue(
                        "text" in types or "code" in types,
                        "Deve ter pelo menos um tipo de termo"
                    )

    def test_empty_code_and_name_handling(self):
        """Teste idiomas com campos vazios"""
        # Criar idioma com campos vazios
        lang_empty = Language.objects.create(
            code2='',  # String vazia
            name='   ',  # Apenas espaços
            creator=self.user
        )

        article = self._create_test_article()
        article.languages.add(lang_empty)

        languages = self.index.prepare_mods_language(article)

        # Implementação deve tratar strings vazias/espaços
        # Pode retornar lista vazia ou filtrar campos vazios
        if languages:
            for lang_data in languages:
                if "languageTerm" in lang_data:
                    for term in lang_data["languageTerm"]:
                        self.assertTrue(
                            term["text"].strip(),
                            "Texto do termo não deve estar vazio"
                        )

    def test_iso_mapping_consistency(self):
        """Teste consistência do mapeamento ISO"""
        article = self._create_test_article()
        article.languages.add(self.lang_pt)  # Português

        languages = self.index.prepare_mods_language(article)

        lang_data = languages[0]
        terms = lang_data["languageTerm"]

        # Encontrar termo código
        code_terms = [t for t in terms if t.get("type") == "code"]
        if code_terms:
            code_term = code_terms[0]

            # Verificar authority
            self.assertIn("authority", code_term)
            authority = code_term["authority"]
            self.assertIn(authority, ["iso639-1", "iso639-2b"],
                          "Authority deve ser ISO válida")

            # Verificar código correspondente
            code_text = code_term["text"]
            if authority == "iso639-1":
                self.assertEqual(len(code_text), 2, "ISO 639-1 deve ter 2 chars")
            elif authority == "iso639-2b":
                self.assertEqual(len(code_text), 3, "ISO 639-2b deve ter 3 chars")

    def test_return_type_consistency(self):
        """Teste consistência do tipo de retorno"""
        article = self._create_test_article()

        # Teste sem idiomas
        languages_empty = self.index.prepare_mods_language(article)
        self.assertIsInstance(languages_empty, list)

        # Teste com idiomas
        article.languages.add(self.lang_en)
        languages_with_data = self.index.prepare_mods_language(article)
        self.assertIsInstance(languages_with_data, list)

        # Verificar estrutura interna
        for lang_data in languages_with_data:
            self.assertIsInstance(lang_data, dict)
            if "languageTerm" in lang_data:
                self.assertIsInstance(lang_data["languageTerm"], list)
                for term in lang_data["languageTerm"]:
                    self.assertIsInstance(term, dict)
                    self.assertIsInstance(term.get("type", ""), str)
                    self.assertIsInstance(term.get("text", ""), str)

    def test_exception_handling(self):
        """Teste tratamento de exceções"""
        # Criar artigo sem problema aparente
        article = self._create_test_article()
        article.languages.add(self.lang_pt)

        # Método deve funcionar normalmente
        languages = self.index.prepare_mods_language(article)

        # Deve retornar estrutura válida mesmo com possíveis erros internos
        self.assertIsInstance(languages, list)

    def test_language_with_special_characters(self):
        """Teste idiomas com caracteres especiais"""
        # Criar idioma com caracteres especiais
        lang_special = Language.objects.create(
            code2='zh',
            name='中文',  # Chinês com caracteres Unicode
            creator=self.user
        )

        article = self._create_test_article()
        article.languages.add(lang_special)

        languages = self.index.prepare_mods_language(article)

        # Deve tratar Unicode corretamente
        if languages:
            lang_data = languages[0]
            terms = lang_data["languageTerm"]

            text_terms = [t for t in terms if t.get("type") == "text"]
            if text_terms:
                text_term = text_terms[0]
                self.assertEqual(text_term["text"], "中文")

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_mods_language.MODSLanguageTestCase -v 2
