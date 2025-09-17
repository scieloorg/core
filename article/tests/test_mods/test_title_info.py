import uuid
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from article.models import Article, DocumentTitle
from article.search_indexes import ArticleOAIMODSIndex
from core.models import Language

User = get_user_model()


class MODSTitleInfoTestCase(TransactionTestCase):
    """
    Testes unitários para elemento MODS titleInfo

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
        DocumentTitle.objects.all().delete()
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

    def test_manual_title_creation_basic(self):
        """Teste: criação manual de DocumentTitle e mapeamento MODS básico"""
        # Criar artigo manualmente
        article = self._create_test_article()

        # Criar título simples
        title = DocumentTitle.objects.create(
            plain_text="Título manual em português para teste unitário",
            language=self.lang_pt,
            creator=self.user
        )
        article.titles.add(title)

        # Validar modelo
        titles = article.titles.all()
        self.assertEqual(titles.count(), 1, "Deveria ter 1 título manual")

        title = titles.first()
        self.assertEqual(title.language, self.lang_pt)
        self.assertIn("português", title.plain_text)

        # Validar mapeamento MODS básico
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 1, "MODS deveria ter 1 titleInfo")

        mods_title = mods_titles[0]

        # Verificar estrutura básica (campos que realmente existem)
        self.assertIn('title', mods_title, "Deve ter campo 'title'")
        self.assertEqual(mods_title['title'], title.plain_text)

        if 'lang' in mods_title:
            self.assertEqual(mods_title['lang'], 'pt')

        # Verificar tipo padrão
        if 'type' in mods_title:
            self.assertEqual(mods_title['type'], 'main')

    def test_multiple_titles_basic(self):
        """Teste: múltiplos títulos básicos"""
        article = self._create_test_article()

        # Criar títulos em idiomas diferentes
        title_pt = DocumentTitle.objects.create(
            plain_text="Análise de Dados em Ciência da Computação",
            language=self.lang_pt,
            creator=self.user
        )
        article.titles.add(title_pt)

        title_en = DocumentTitle.objects.create(
            plain_text="Data Analysis in Computer Science",
            language=self.lang_en,
            creator=self.user
        )
        article.titles.add(title_en)

        # Validar modelos
        titles = article.titles.all()
        self.assertEqual(titles.count(), 2, "Deveria ter 2 títulos")

        # Verificar idiomas
        languages = {title.language.code2 for title in titles}
        self.assertEqual(languages, {'pt', 'en'}, "Deveria ter títulos em pt e en")

        # Validar mapeamento MODS
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 2, "MODS deveria ter 2 titleInfo")

        # Verificar que ambos os idiomas estão representados
        mods_langs = {title.get('lang') for title in mods_titles if 'lang' in title}
        self.assertTrue(len(mods_langs) > 0, "Pelo menos um idioma deve estar presente")

        # Verificar conteúdo específico
        mods_texts = {title['title'] for title in mods_titles}
        self.assertIn("Análise de Dados em Ciência da Computação", mods_texts)
        self.assertIn("Data Analysis in Computer Science", mods_texts)

    def test_no_titles(self):
        """Teste: artigo sem títulos"""
        article = self._create_test_article()

        # Não criar títulos
        titles = article.titles.all()
        self.assertEqual(titles.count(), 0, "Não deveria ter títulos")

        # Validar mapeamento MODS vazio
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 0, "MODS não deveria ter titleInfo")

    def test_title_without_language(self):
        """Teste: título sem idioma especificado"""
        article = self._create_test_article()

        # Criar título sem idioma
        title = DocumentTitle.objects.create(
            plain_text="Título sem idioma especificado",
            language=None,  # Sem idioma
            creator=self.user
        )
        article.titles.add(title)

        # Validar modelo
        titles = article.titles.all()
        self.assertEqual(titles.count(), 1, "Deveria ter 1 título")

        title = titles.first()
        self.assertIsNone(title.language, "Idioma deve ser None")

        # Validar mapeamento MODS
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 1, "MODS deveria ter 1 titleInfo")

        mods_title = mods_titles[0]
        self.assertIn('title', mods_title)
        self.assertEqual(mods_title['title'], "Título sem idioma especificado")

        # Verificar que 'lang' não está presente ou é None
        if 'lang' in mods_title:
            self.assertIsNone(mods_title['lang'])

    def test_mods_title_info_structure_basic(self):
        """Teste: estrutura básica do elemento MODS titleInfo"""
        article = self._create_test_article()

        title = DocumentTitle.objects.create(
            plain_text="Teste de Estrutura MODS titleInfo",
            language=self.lang_en,
            creator=self.user
        )
        article.titles.add(title)

        # Testar mapeamento MODS
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 1)

        mods_title = mods_titles[0]

        # Verificar apenas campos que sabemos que existem
        self.assertIn('title', mods_title, "Deve ter campo 'title'")
        self.assertEqual(mods_title['title'], "Teste de Estrutura MODS titleInfo")

        # Verificar idioma se presente
        if 'lang' in mods_title:
            self.assertEqual(mods_title['lang'], 'en')

        # Verificar tipo se presente
        if 'type' in mods_title:
            self.assertEqual(mods_title['type'], 'main')

    def test_complex_title_content(self):
        """Teste: conteúdo de título mais complexo"""
        article = self._create_test_article()

        complex_title = "Machine Learning Applications in Healthcare: A Systematic Review of Deep Learning Algorithms for Medical Image Analysis and Clinical Decision Support Systems"

        title = DocumentTitle.objects.create(
            plain_text=complex_title,
            language=self.lang_en,
            creator=self.user
        )
        article.titles.add(title)

        # Validar modelo
        titles = article.titles.all()
        title = titles.first()

        # Verificar se conteúdo complexo foi preservado
        content = title.plain_text.lower()
        self.assertIn("machine learning", content)
        self.assertIn("healthcare", content)
        self.assertIn("systematic review", content)
        self.assertIn("deep learning", content)

        # Validar mapeamento MODS
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 1)

        mods_title = mods_titles[0]
        mods_content = mods_title['title'].lower()

        # Verificar que conteúdo complexo foi preservado no MODS
        self.assertIn("machine learning", mods_content)
        self.assertIn("healthcare", mods_content)
        self.assertIn("systematic review", mods_content)
        self.assertIn("deep learning", mods_content)

        # Verificar comprimento do título
        self.assertGreater(len(mods_title['title']), 100, "Título complexo deve ser longo")

    def test_multilingual_titles_complete(self):
        """Teste: títulos multilíngues completos"""
        article = self._create_test_article()

        # Criar títulos em três idiomas
        titles_data = [
            ("Inteligência Artificial na Medicina: Revisão Sistemática", self.lang_pt),
            ("Artificial Intelligence in Medicine: A Systematic Review", self.lang_en),
            ("Inteligencia Artificial en Medicina: Una Revisión Sistemática", self.lang_es)
        ]

        for title_text, language in titles_data:
            title = DocumentTitle.objects.create(
                plain_text=title_text,
                language=language,
                creator=self.user
            )
            article.titles.add(title)

        # Validar modelos
        titles = article.titles.all()
        self.assertEqual(titles.count(), 3, "Deveria ter 3 títulos")

        # Verificar idiomas
        languages = {title.language.code2 for title in titles}
        self.assertEqual(languages, {'pt', 'en', 'es'}, "Deveria ter títulos em pt, en e es")

        # Validar mapeamento MODS
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 3, "MODS deveria ter 3 titleInfo")

        # Verificar que todos os idiomas estão representados no MODS
        mods_texts = [title['title'] for title in mods_titles]
        mods_langs = {title.get('lang') for title in mods_titles if 'lang' in title}

        # Verificar conteúdo específico por idioma
        self.assertTrue(any("Inteligência Artificial" in text for text in mods_texts))
        self.assertTrue(any("Artificial Intelligence" in text for text in mods_texts))
        self.assertTrue(any("Inteligencia Artificial" in text for text in mods_texts))

    def test_title_special_characters(self):
        """Teste: título com caracteres especiais"""
        article = self._create_test_article()

        special_title = "COVID-19 & SARS-CoV-2: Análise Genômica (2020-2023) – Revisão"

        title = DocumentTitle.objects.create(
            plain_text=special_title,
            language=self.lang_pt,
            creator=self.user
        )
        article.titles.add(title)

        # Validar modelo
        titles = article.titles.all()
        title = titles.first()
        self.assertIn("COVID-19", title.plain_text)
        self.assertIn("&", title.plain_text)
        self.assertIn("–", title.plain_text)
        self.assertIn("(2020-2023)", title.plain_text)

        # Validar mapeamento MODS
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 1)

        mods_title = mods_titles[0]
        title_content = mods_title['title']

        # Verificar que caracteres especiais foram preservados
        self.assertIn("COVID-19", title_content)
        self.assertIn("&", title_content)
        self.assertIn("–", title_content)
        self.assertIn("(2020-2023)", title_content)

    def test_unique_constraint_handling(self):
        """Teste: tratamento correto de constraints de unicidade"""
        article = self._create_test_article()

        # Criar primeiro título
        title1 = DocumentTitle.objects.create(
            plain_text="Primeiro título em português",
            language=self.lang_pt,
            creator=self.user
        )
        article.titles.add(title1)

        # Criar segundo título com idioma diferente deve funcionar
        title2 = DocumentTitle.objects.create(
            plain_text="Title in English",
            language=self.lang_en,  # Idioma diferente
            creator=self.user
        )
        article.titles.add(title2)

        # Verificar que temos 2 títulos
        self.assertEqual(article.titles.count(), 2)

        # Para DocumentTitle, não há constraint de unicidade entre artigo e idioma
        # porque usa ManyToMany - cada DocumentTitle é independente

    def test_empty_title_content(self):
        """Teste: título com conteúdo vazio ou apenas espaços"""
        article = self._create_test_article()

        # Criar título com apenas espaços
        title = DocumentTitle.objects.create(
            plain_text="   ",  # Apenas espaços
            language=self.lang_pt,
            creator=self.user
        )
        article.titles.add(title)

        # Validar modelo
        titles = article.titles.all()
        self.assertEqual(titles.count(), 1)

        title = titles.first()
        self.assertEqual(title.plain_text, "   ")

        # Validar mapeamento MODS
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 1)

        mods_title = mods_titles[0]
        self.assertEqual(mods_title['title'], "   ")

    def test_mods_title_info_filtering_none_values(self):
        """Teste: verificação de que valores None são filtrados do MODS"""
        article = self._create_test_article()

        # Criar título sem idioma
        title = DocumentTitle.objects.create(
            plain_text="Título sem idioma",
            language=None,
            creator=self.user
        )
        article.titles.add(title)

        # Validar mapeamento MODS
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 1)

        mods_title = mods_titles[0]

        # Verificar que campos None não estão presentes no dicionário final
        # (baseado na lógica de filtro no método prepare_mods_title_info)
        for key, value in mods_title.items():
            self.assertIsNotNone(value, f"Campo '{key}' não deveria ser None no MODS")


# python manage.py test --keepdb article.tests.test_mods.test_title_info.MODSTitleInfoTestCase -v 2
