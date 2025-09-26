import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from article.models import Article, DocumentAbstract
from article.search_indexes import ArticleOAIMODSIndex
from core.models import Language

User = get_user_model()


class MODSAbstractTestCase(TestCase):
    """
    Testes unitários otimizados para elemento abstract MODS
    Usa TestCase para melhor performance
    """

    @classmethod
    def setUpTestData(cls):
        """Dados compartilhados entre testes para melhor performance"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

        # Criar idiomas uma vez
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

    def _create_test_article(self):
        """Helper otimizado para criar artigo"""
        return Article.objects.create(
            pid_v3=f'test-{uuid.uuid4().hex[:8]}',
            article_type='research-article',
            creator=self.user
        )

    def test_mods_no_abstracts(self):
        """Teste: artigo sem resumos"""
        article = self._create_test_article()

        mods_abstracts = self.index.prepare_mods_abstract(article)

        self.assertEqual(len(mods_abstracts), 0)

    def test_mods_single_abstract_with_language(self):
        """Teste: resumo único com idioma"""
        article = self._create_test_article()

        DocumentAbstract.objects.create(
            article=article,
            plain_text="Resumo em português para teste.",
            language=self.lang_pt,
            creator=self.user
        )

        mods_abstracts = self.index.prepare_mods_abstract(article)

        self.assertEqual(len(mods_abstracts), 1)

        abstract = mods_abstracts[0]
        self.assertEqual(abstract['text'], "Resumo em português para teste.")
        self.assertEqual(abstract['lang'], 'pt')

    def test_mods_single_abstract_without_language(self):
        """Teste: resumo sem idioma"""
        article = self._create_test_article()

        DocumentAbstract.objects.create(
            article=article,
            plain_text="Resumo sem idioma.",
            language=None,
            creator=self.user
        )

        mods_abstracts = self.index.prepare_mods_abstract(article)

        self.assertEqual(len(mods_abstracts), 1)

        abstract = mods_abstracts[0]
        self.assertEqual(abstract['text'], "Resumo sem idioma.")
        self.assertNotIn('lang', abstract)

    def test_mods_multiple_abstracts_different_languages(self):
        """Teste: múltiplos resumos em idiomas diferentes"""
        article = self._create_test_article()

        # Criar abstracts em batch para melhor performance
        abstracts = [
            DocumentAbstract(
                article=article,
                plain_text="Resumo em português.",
                language=self.lang_pt,
                creator=self.user
            ),
            DocumentAbstract(
                article=article,
                plain_text="Abstract in English.",
                language=self.lang_en,
                creator=self.user
            ),
            DocumentAbstract(
                article=article,
                plain_text="Resumen en español.",
                language=self.lang_es,
                creator=self.user
            )
        ]
        DocumentAbstract.objects.bulk_create(abstracts)

        mods_abstracts = self.index.prepare_mods_abstract(article)

        self.assertEqual(len(mods_abstracts), 3)

        # Verificar idiomas presentes
        langs = {abs['lang'] for abs in mods_abstracts}
        self.assertEqual(langs, {'pt', 'en', 'es'})

    def test_mods_display_label_mapping(self):
        """Teste: mapeamento de displayLabel por idioma"""
        article = self._create_test_article()

        DocumentAbstract.objects.create(
            article=article,
            plain_text="Resumo teste.",
            language=self.lang_pt,
            creator=self.user
        )

        mods_abstracts = self.index.prepare_mods_abstract(article)

        abstract = mods_abstracts[0]

        # Se displayLabel existir, deve estar correto
        if 'displayLabel' in abstract:
            self.assertEqual(abstract['displayLabel'], 'Resumo')

    def test_mods_empty_text_preserved(self):
        """Teste: texto vazio é preservado"""
        article = self._create_test_article()

        DocumentAbstract.objects.create(
            article=article,
            plain_text="",
            language=self.lang_en,
            creator=self.user
        )

        mods_abstracts = self.index.prepare_mods_abstract(article)

        self.assertEqual(len(mods_abstracts), 1)
        self.assertEqual(mods_abstracts[0]['text'], "")

    def test_mods_whitespace_preserved(self):
        """Teste: espaços em branco são preservados"""
        article = self._create_test_article()

        whitespace_text = "   \n\t   \n   "

        DocumentAbstract.objects.create(
            article=article,
            plain_text=whitespace_text,
            language=self.lang_en,
            creator=self.user
        )

        mods_abstracts = self.index.prepare_mods_abstract(article)

        self.assertEqual(mods_abstracts[0]['text'], whitespace_text)

    def test_mods_complex_structured_content(self):
        """Teste: conteúdo estruturado complexo"""
        article = self._create_test_article()

        complex_text = (
            "Objective: Evaluate methodology. "
            "Methods: Systematic review. "
            "Results: 78% improvement (p<0.05). "
            "Conclusion: Effective for applications."
        )

        DocumentAbstract.objects.create(
            article=article,
            plain_text=complex_text,
            language=self.lang_en,
            creator=self.user
        )

        mods_abstracts = self.index.prepare_mods_abstract(article)

        abstract_text = mods_abstracts[0]['text'].lower()

        # Verificar preservação de estrutura
        self.assertIn("objective", abstract_text)
        self.assertIn("methods", abstract_text)
        self.assertIn("results", abstract_text)
        self.assertIn("conclusion", abstract_text)
        self.assertIn("p<0.05", abstract_text)

    def test_mods_mixed_language_scenario(self):
        """Teste: cenário misto - com e sem idioma"""
        article = self._create_test_article()

        # Abstract com idioma
        DocumentAbstract.objects.create(
            article=article,
            plain_text="Resumo com idioma.",
            language=self.lang_pt,
            creator=self.user
        )

        # Abstract sem idioma
        DocumentAbstract.objects.create(
            article=article,
            plain_text="Abstract without language.",
            language=None,
            creator=self.user
        )

        mods_abstracts = self.index.prepare_mods_abstract(article)

        self.assertEqual(len(mods_abstracts), 2)

        # Contar por presença de idioma
        with_lang = [abs for abs in mods_abstracts if 'lang' in abs]
        without_lang = [abs for abs in mods_abstracts if 'lang' not in abs]

        self.assertEqual(len(with_lang), 1)
        self.assertEqual(len(without_lang), 1)
        self.assertEqual(with_lang[0]['lang'], 'pt')

    def test_mods_abstract_structure_validation(self):
        """Teste: validação da estrutura MODS"""
        article = self._create_test_article()

        DocumentAbstract.objects.create(
            article=article,
            plain_text="Teste de estrutura.",
            language=self.lang_en,
            creator=self.user
        )

        mods_abstracts = self.index.prepare_mods_abstract(article)

        abstract = mods_abstracts[0]

        # Campos obrigatórios
        self.assertIn('text', abstract)
        self.assertIsInstance(abstract['text'], str)

        # Campos opcionais devem ser strings se presentes
        if 'lang' in abstract:
            self.assertIsInstance(abstract['lang'], str)
        if 'displayLabel' in abstract:
            self.assertIsInstance(abstract['displayLabel'], str)

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_abstract.MODSAbstractTestCase --parallel 2 -v 2
