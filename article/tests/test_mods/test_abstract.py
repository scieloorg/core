import uuid
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from article.models import Article, DocumentAbstract
from article.search_indexes import ArticleOAIMODSIndex
from core.models import Language

User = get_user_model()


class MODSAbstractTestCase(TransactionTestCase):
    """
    Testes unitários focados no índice MODS para elemento abstract

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
        # Limpar dados criados no teste
        DocumentAbstract.objects.all().delete()
        Article.objects.all().delete()
        super().tearDown()

    def _create_test_article(self, sps_pkg_name=None):
        """Helper para criar artigo de teste único"""
        if not sps_pkg_name:
            sps_pkg_name = f'test-{uuid.uuid4().hex[:12]}'

        return Article.objects.create(
            sps_pkg_name=sps_pkg_name,
            pid_v3=f'test-{uuid.uuid4().hex[:12]}',
            article_type='research-article',
            creator=self.user
        )

    def test_document_abstract_creation_basic(self):
        """Teste único para validar criação do modelo DocumentAbstract"""
        article = self._create_test_article()

        # Criar resumo básico
        abstract = DocumentAbstract.objects.create(
            article=article,
            plain_text="Resumo de teste para validação do modelo.",
            language=self.lang_pt,
            creator=self.user
        )

        # Validações básicas do modelo
        self.assertIsNotNone(abstract.id, "Abstract deve ter ID após criação")
        self.assertEqual(abstract.article, article, "Article deve estar corretamente associado")
        self.assertEqual(abstract.language, self.lang_pt, "Idioma deve estar correto")
        self.assertEqual(abstract.creator, self.user, "Creator deve estar correto")
        self.assertIn("teste", abstract.plain_text, "Texto deve estar correto")

        # Verificar relacionamento reverso
        self.assertEqual(article.abstracts.count(), 1, "Article deve ter 1 abstract")
        self.assertEqual(article.abstracts.first(), abstract, "Relacionamento reverso deve funcionar")

    def test_mods_index_no_abstracts(self):
        """Teste índice MODS: artigo sem resumos"""
        article = self._create_test_article()

        # Validar mapeamento MODS vazio
        mods_abstracts = self.index.prepare_mods_abstract(article)
        self.assertEqual(len(mods_abstracts), 0, "MODS não deveria ter abstracts")

    def test_mods_index_single_abstract(self):
        """Teste índice MODS: resumo único com idioma"""
        article = self._create_test_article()

        DocumentAbstract.objects.create(
            article=article,
            plain_text="Resumo único em português para teste do índice MODS.",
            language=self.lang_pt,
            creator=self.user
        )

        # Validar mapeamento MODS básico
        mods_abstracts = self.index.prepare_mods_abstract(article)
        self.assertEqual(len(mods_abstracts), 1, "MODS deveria ter 1 abstract")

        mods_abstract = mods_abstracts[0]

        # Verificar estrutura básica
        self.assertIn('text', mods_abstract, "Deve ter campo 'text'")
        self.assertEqual(mods_abstract['text'], "Resumo único em português para teste do índice MODS.")

        # Verificar idioma se presente
        if 'lang' in mods_abstract:
            self.assertEqual(mods_abstract['lang'], 'pt')

        # Verificar displayLabel se presente
        if 'displayLabel' in mods_abstract:
            self.assertEqual(mods_abstract['displayLabel'], 'Resumo')

    def test_mods_index_multiple_abstracts(self):
        """Teste índice MODS: múltiplos resumos em idiomas diferentes"""
        article = self._create_test_article()

        # Criar resumos em idiomas diferentes
        DocumentAbstract.objects.create(
            article=article,
            plain_text="Resumo em português para teste multilíngue.",
            language=self.lang_pt,
            creator=self.user
        )

        DocumentAbstract.objects.create(
            article=article,
            plain_text="Abstract in English for multilingual test.",
            language=self.lang_en,
            creator=self.user
        )

        DocumentAbstract.objects.create(
            article=article,
            plain_text="Resumen en español para prueba multilingüe.",
            language=self.lang_es,
            creator=self.user
        )

        # Validar mapeamento MODS
        mods_abstracts = self.index.prepare_mods_abstract(article)
        self.assertEqual(len(mods_abstracts), 3, "MODS deveria ter 3 abstracts")

        # Verificar que todos têm estrutura básica
        for mods_abstract in mods_abstracts:
            self.assertIn('text', mods_abstract, "Cada abstract deve ter campo 'text'")
            self.assertTrue(len(mods_abstract['text']) > 0, "Text não deve estar vazio")

        # Verificar idiomas se presentes
        mods_langs = {abs.get('lang') for abs in mods_abstracts if 'lang' in abs}
        expected_langs = {'pt', 'en', 'es'}
        self.assertEqual(mods_langs, expected_langs, "Todos os idiomas devem estar presentes")

        # Verificar displayLabels se presentes
        display_labels = {abs.get('displayLabel') for abs in mods_abstracts if 'displayLabel' in abs}
        expected_labels = {'Resumo', 'Abstract', 'Resumen'}
        if display_labels:  # Só verifica se existem displayLabels
            self.assertEqual(display_labels, expected_labels, "DisplayLabels devem estar corretos")

    def test_mods_index_abstract_without_language(self):
        """Teste índice MODS: resumo sem idioma especificado"""
        article = self._create_test_article()

        DocumentAbstract.objects.create(
            article=article,
            plain_text="Resumo sem idioma especificado para teste do índice.",
            language=None,  # Sem idioma
            creator=self.user
        )

        # Validar mapeamento MODS
        mods_abstracts = self.index.prepare_mods_abstract(article)
        self.assertEqual(len(mods_abstracts), 1, "MODS deveria ter 1 abstract")

        mods_abstract = mods_abstracts[0]
        self.assertIn('text', mods_abstract)
        self.assertIn("sem idioma", mods_abstract['text'].lower())

        # Não deve ter campo lang
        self.assertNotIn('lang', mods_abstract, "Não deve ter campo 'lang' quando language é None")
        self.assertNotIn('displayLabel', mods_abstract, "Não deve ter displayLabel quando language é None")

    def test_mods_index_complex_abstract_content(self):
        """Teste índice MODS: conteúdo de resumo estruturado complexo"""
        article = self._create_test_article()

        complex_text = """
        Objective: To evaluate the effectiveness of novel methodology in clinical settings.
        Methods: We conducted a systematic review with 150 randomized controlled trials.
        Results: Significant improvement was observed in 78% of cases (p<0.05).
        Conclusion: The methodology proves effective for real-world applications.
        Keywords: methodology, clinical trials, systematic review.
        """

        DocumentAbstract.objects.create(
            article=article,
            plain_text=complex_text,
            language=self.lang_en,
            creator=self.user
        )

        # Validar mapeamento MODS
        mods_abstracts = self.index.prepare_mods_abstract(article)
        self.assertEqual(len(mods_abstracts), 1)

        mods_abstract = mods_abstracts[0]
        mods_content = mods_abstract['text'].lower()

        # Verificar que conteúdo estruturado foi preservado no MODS
        self.assertIn("objective", mods_content, "Seção Objective deve estar presente")
        self.assertIn("methods", mods_content, "Seção Methods deve estar presente")
        self.assertIn("results", mods_content, "Seção Results deve estar presente")
        self.assertIn("conclusion", mods_content, "Seção Conclusion deve estar presente")
        self.assertIn("systematic review", mods_content, "Termo específico deve estar presente")
        self.assertIn("p<0.05", mods_content, "Dados estatísticos devem estar presentes")

        # Verificar idioma
        if 'lang' in mods_abstract:
            self.assertEqual(mods_abstract['lang'], 'en')

        # Verificar displayLabel
        if 'displayLabel' in mods_abstract:
            self.assertEqual(mods_abstract['displayLabel'], 'Abstract')

    def test_mods_index_empty_text_handling(self):
        """Teste índice MODS: tratamento de texto vazio"""
        article = self._create_test_article()

        # Criar abstract com texto vazio
        DocumentAbstract.objects.create(
            article=article,
            plain_text="",  # Texto vazio
            language=self.lang_pt,
            creator=self.user
        )

        # Validar mapeamento MODS
        mods_abstracts = self.index.prepare_mods_abstract(article)
        self.assertEqual(len(mods_abstracts), 1, "MODS deveria incluir abstract mesmo com texto vazio")

        mods_abstract = mods_abstracts[0]
        self.assertIn('text', mods_abstract)
        self.assertEqual(mods_abstract['text'], "", "Texto vazio deve ser preservado")

    def test_mods_index_whitespace_text_handling(self):
        """Teste índice MODS: tratamento de texto com apenas espaços em branco"""
        article = self._create_test_article()

        whitespace_text = "   \n\t   \n   "  # Apenas espaços em branco

        DocumentAbstract.objects.create(
            article=article,
            plain_text=whitespace_text,
            language=self.lang_en,
            creator=self.user
        )

        # Validar mapeamento MODS
        mods_abstracts = self.index.prepare_mods_abstract(article)
        self.assertEqual(len(mods_abstracts), 1, "MODS deveria incluir abstract com whitespace")

        mods_abstract = mods_abstracts[0]
        self.assertIn('text', mods_abstract)
        self.assertEqual(mods_abstract['text'], whitespace_text, "Whitespace deve ser preservado como está")

    def test_mods_index_mixed_scenarios(self):
        """Teste índice MODS: cenário misto com abstracts variados"""
        article = self._create_test_article()

        # Abstract normal com idioma
        DocumentAbstract.objects.create(
            article=article,
            plain_text="Resumo normal em português.",
            language=self.lang_pt,
            creator=self.user
        )

        # Abstract sem idioma
        DocumentAbstract.objects.create(
            article=article,
            plain_text="Abstract without language specification.",
            language=None,
            creator=self.user
        )

        # Abstract com texto complexo
        DocumentAbstract.objects.create(
            article=article,
            plain_text="Resumen complejo con métodos, resultados y conclusiones específicas.",
            language=self.lang_es,
            creator=self.user
        )

        # Validar mapeamento MODS
        mods_abstracts = self.index.prepare_mods_abstract(article)
        self.assertEqual(len(mods_abstracts), 3, "MODS deveria ter 3 abstracts no cenário misto")

        # Verificar que todos têm estrutura básica
        for i, mods_abstract in enumerate(mods_abstracts):
            self.assertIn('text', mods_abstract, f"Abstract {i} deve ter campo 'text'")
            self.assertTrue(len(mods_abstract['text']) > 0, f"Abstract {i} deve ter texto não vazio")

        # Contar abstracts com e sem idioma
        with_lang = [abs for abs in mods_abstracts if 'lang' in abs]
        without_lang = [abs for abs in mods_abstracts if 'lang' not in abs]

        self.assertEqual(len(with_lang), 2, "Deveria ter 2 abstracts com idioma")
        self.assertEqual(len(without_lang), 1, "Deveria ter 1 abstract sem idioma")

        # Verificar idiomas específicos
        langs_present = {abs['lang'] for abs in with_lang}
        expected_langs = {'pt', 'es'}
        self.assertEqual(langs_present, expected_langs, "Idiomas pt e es devem estar presentes")

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_abstract.MODSAbstractTestCase -v 2
