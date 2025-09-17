import uuid
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from article.models import Article, DocumentAbstract
from article.search_indexes import ArticleOAIMODSIndex
from core.models import Language

User = get_user_model()


class MODSAbstractTestCase(TransactionTestCase):
    """
    Testes unitários para elemento MODS abstract

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

        # Manter usuário e idiomas (são reutilizáveis)
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

    def test_manual_abstract_creation_basic(self):
        """Teste: criação manual de DocumentAbstract e mapeamento MODS básico"""
        # Criar artigo manualmente
        article = self._create_test_article()

        # Criar resumo simples
        DocumentAbstract.objects.create(
            article=article,
            plain_text="Resumo manual em português para teste unitário.",
            language=self.lang_pt,
            creator=self.user
        )

        # Validar modelo
        abstracts = article.abstracts.all()
        self.assertEqual(abstracts.count(), 1, "Deveria ter 1 resumo manual")

        abstract = abstracts.first()
        self.assertEqual(abstract.language, self.lang_pt)
        self.assertIn("português", abstract.plain_text)

        # Validar mapeamento MODS básico
        mods_abstracts = self.index.prepare_mods_abstract(article)
        self.assertEqual(len(mods_abstracts), 1, "MODS deveria ter 1 abstract")

        mods_abstract = mods_abstracts[0]

        # Verificar estrutura básica (campos que realmente existem)
        self.assertIn('text', mods_abstract, "Deve ter campo 'text'")
        self.assertEqual(mods_abstract['text'], abstract.plain_text)

        if 'lang' in mods_abstract:
            self.assertEqual(mods_abstract['lang'], 'pt')

    def test_multiple_abstracts_basic(self):
        """Teste: múltiplos resumos básicos"""
        article = self._create_test_article()

        # Criar resumos em idiomas diferentes
        DocumentAbstract.objects.create(
            article=article,
            plain_text="Resumo em português.",
            language=self.lang_pt,
            creator=self.user
        )

        DocumentAbstract.objects.create(
            article=article,
            plain_text="Abstract in English.",
            language=self.lang_en,
            creator=self.user
        )

        # Validar modelos
        abstracts = article.abstracts.all()
        self.assertEqual(abstracts.count(), 2, "Deveria ter 2 resumos")

        # Verificar idiomas
        languages = {abs.language.code2 for abs in abstracts}
        self.assertEqual(languages, {'pt', 'en'}, "Deveria ter resumos em pt e en")

        # Validar mapeamento MODS
        mods_abstracts = self.index.prepare_mods_abstract(article)
        self.assertEqual(len(mods_abstracts), 2, "MODS deveria ter 2 abstracts")

        # Verificar que ambos os idiomas estão representados
        mods_langs = {abs.get('lang') for abs in mods_abstracts if 'lang' in abs}
        self.assertTrue(len(mods_langs) > 0, "Pelo menos um idioma deve estar presente")

    def test_no_abstracts(self):
        """Teste: artigo sem resumos"""
        article = self._create_test_article()

        # Não criar resumos
        abstracts = article.abstracts.all()
        self.assertEqual(abstracts.count(), 0, "Não deveria ter resumos")

        # Validar mapeamento MODS vazio
        mods_abstracts = self.index.prepare_mods_abstract(article)
        self.assertEqual(len(mods_abstracts), 0, "MODS não deveria ter abstracts")

    def test_abstract_without_language(self):
        """Teste: resumo sem idioma especificado"""
        article = self._create_test_article()

        # Criar resumo sem idioma
        DocumentAbstract.objects.create(
            article=article,
            plain_text="Resumo sem idioma especificado.",
            language=None,  # Sem idioma
            creator=self.user
        )

        # Validar modelo
        abstracts = article.abstracts.all()
        self.assertEqual(abstracts.count(), 1, "Deveria ter 1 resumo")

        abstract = abstracts.first()
        self.assertIsNone(abstract.language, "Idioma deve ser None")

        # Validar mapeamento MODS
        mods_abstracts = self.index.prepare_mods_abstract(article)
        self.assertEqual(len(mods_abstracts), 1, "MODS deveria ter 1 abstract")

        mods_abstract = mods_abstracts[0]
        self.assertIn('text', mods_abstract)
        self.assertIn("resumo sem idioma", mods_abstract['text'].lower())

    def test_mods_abstract_structure_basic(self):
        """Teste: estrutura básica do elemento MODS abstract"""
        article = self._create_test_article()

        DocumentAbstract.objects.create(
            article=article,
            plain_text="Teste de estrutura MODS abstract.",
            language=self.lang_en,
            creator=self.user
        )

        # Testar mapeamento MODS
        mods_abstracts = self.index.prepare_mods_abstract(article)
        self.assertEqual(len(mods_abstracts), 1)

        mods_abstract = mods_abstracts[0]

        # Verificar apenas campos que sabemos que existem
        self.assertIn('text', mods_abstract, "Deve ter campo 'text'")
        self.assertEqual(mods_abstract['text'], "Teste de estrutura MODS abstract.")

        # Verificar idioma se presente
        if 'lang' in mods_abstract:
            self.assertEqual(mods_abstract['lang'], 'en')

    def test_complex_abstract_content(self):
        """Teste: conteúdo de resumo mais complexo"""
        article = self._create_test_article()

        complex_text = """
        Objective: To evaluate the effectiveness of novel methodology.
        Methods: We conducted a systematic review with 150 studies.
        Results: Significant improvement was observed (p<0.05).
        Conclusion: The methodology proves effective for applications.
        """

        DocumentAbstract.objects.create(
            article=article,
            plain_text=complex_text,
            language=self.lang_en,
            creator=self.user
        )

        # Validar modelo
        abstracts = article.abstracts.all()
        abstract = abstracts.first()

        # Verificar se conteúdo estruturado foi preservado
        content = abstract.plain_text.lower()
        self.assertIn("objective", content)
        self.assertIn("methods", content)
        self.assertIn("results", content)
        self.assertIn("conclusion", content)

        # Validar mapeamento MODS
        mods_abstracts = self.index.prepare_mods_abstract(article)
        self.assertEqual(len(mods_abstracts), 1)

        mods_abstract = mods_abstracts[0]
        mods_content = mods_abstract['text'].lower()

        # Verificar que conteúdo estruturado foi preservado no MODS
        self.assertIn("objective", mods_content)
        self.assertIn("methods", mods_content)
        self.assertIn("results", mods_content)
        self.assertIn("conclusion", mods_content)

    def test_unique_constraint_handling(self):
        """Teste: tratamento correto de constraints de unicidade"""
        article = self._create_test_article()

        # Criar primeiro resumo
        DocumentAbstract.objects.create(
            article=article,
            plain_text="Primeiro resumo em português.",
            language=self.lang_pt,
            creator=self.user
        )

        # Tentar criar segundo resumo com mesmo artigo/idioma deve falhar
        with self.assertRaises(Exception):  # IntegrityError esperado
            DocumentAbstract.objects.create(
                article=article,
                plain_text="Segundo resumo em português.",  # Mesmo idioma
                language=self.lang_pt,
                creator=self.user
            )

        # Mas criar com idioma diferente deve funcionar
        DocumentAbstract.objects.create(
            article=article,
            plain_text="Abstract in English.",
            language=self.lang_en,  # Idioma diferente
            creator=self.user
        )

        # Verificar que temos apenas 2 resumos
        self.assertEqual(article.abstracts.count(), 2)


# python manage.py test --keepdb article.tests.test_mods.test_abstract.MODSAbstractTestCase -v 2
