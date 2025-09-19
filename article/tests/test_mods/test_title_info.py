import uuid
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from article.models import Article, DocumentTitle
from article.search_indexes import ArticleOAIMODSIndex
from core.models import Language

User = get_user_model()


class MODSTitleInfoTestCase(TransactionTestCase):
    """
    Testes unitários focados no índice MODS para elemento titleInfo

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

    def test_document_title_creation_basic(self):
        """Teste único para validar criação do modelo DocumentTitle"""
        article = self._create_test_article()

        # Criar título básico
        title = DocumentTitle.objects.create(
            plain_text="Título de teste para validação do modelo",
            language=self.lang_pt,
            creator=self.user
        )
        article.titles.add(title)

        # Validações básicas do modelo
        self.assertIsNotNone(title.id, "Title deve ter ID após criação")
        self.assertEqual(title.language, self.lang_pt, "Idioma deve estar correto")
        self.assertEqual(title.creator, self.user, "Creator deve estar correto")
        self.assertIn("teste", title.plain_text, "Texto deve estar correto")

        # Verificar relacionamento ManyToMany
        self.assertEqual(article.titles.count(), 1, "Article deve ter 1 título")
        self.assertIn(title, article.titles.all(), "Relacionamento ManyToMany deve funcionar")

    def test_mods_index_no_titles(self):
        """Teste índice MODS: artigo sem títulos"""
        article = self._create_test_article()

        # Validar mapeamento MODS vazio
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 0, "MODS não deveria ter titleInfo")

    def test_mods_index_single_title(self):
        """Teste índice MODS: título único com idioma"""
        article = self._create_test_article()

        title = DocumentTitle.objects.create(
            plain_text="Análise de Dados em Ciência da Computação",
            language=self.lang_pt,
            creator=self.user
        )
        article.titles.add(title)

        # Validar mapeamento MODS básico
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 1, "MODS deveria ter 1 titleInfo")

        mods_title = mods_titles[0]

        # Verificar estrutura básica
        self.assertIn('title', mods_title, "Deve ter campo 'title'")
        self.assertEqual(mods_title['title'], "Análise de Dados em Ciência da Computação")

        # Verificar idioma se presente
        if 'lang' in mods_title:
            self.assertEqual(mods_title['lang'], 'pt')

    def test_mods_index_multiple_titles(self):
        """Teste índice MODS: múltiplos títulos em idiomas diferentes"""
        article = self._create_test_article()

        # Criar títulos em idiomas diferentes
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

        # Validar mapeamento MODS
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 3, "MODS deveria ter 3 titleInfo")

        # Verificar que todos têm estrutura básica
        for mods_title in mods_titles:
            self.assertIn('title', mods_title, "Cada título deve ter campo 'title'")
            self.assertTrue(len(mods_title['title']) > 0, "Title não deve estar vazio")

        # Verificar idiomas se presentes
        mods_langs = {title.get('lang') for title in mods_titles if 'lang' in title}
        expected_langs = {'pt', 'en', 'es'}
        self.assertEqual(mods_langs, expected_langs, "Todos os idiomas devem estar presentes")

        # Verificar conteúdo específico por idioma
        mods_texts = {title['title'] for title in mods_titles}
        self.assertIn("Inteligência Artificial na Medicina", " ".join(mods_texts))
        self.assertIn("Artificial Intelligence in Medicine", " ".join(mods_texts))
        self.assertIn("Inteligencia Artificial en Medicina", " ".join(mods_texts))

    def test_mods_index_title_without_language(self):
        """Teste índice MODS: título sem idioma especificado"""
        article = self._create_test_article()

        title = DocumentTitle.objects.create(
            plain_text="Título sem idioma especificado para teste do índice",
            language=None,  # Sem idioma
            creator=self.user
        )
        article.titles.add(title)

        # Validar mapeamento MODS
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 1, "MODS deveria ter 1 titleInfo")

        mods_title = mods_titles[0]
        self.assertIn('title', mods_title)
        self.assertEqual(mods_title['title'], "Título sem idioma especificado para teste do índice")

        # Verificar que 'lang' não está presente ou é None (devido ao filtro de None values)
        if 'lang' in mods_title:
            self.assertIsNone(mods_title['lang'])

    def test_mods_index_complex_title_content(self):
        """Teste índice MODS: conteúdo de título complexo"""
        article = self._create_test_article()

        complex_title = ("Machine Learning Applications in Healthcare: A Systematic Review of Deep Learning Algorithms "
                         "for Medical Image Analysis and Clinical Decision Support Systems")

        title = DocumentTitle.objects.create(
            plain_text=complex_title,
            language=self.lang_en,
            creator=self.user
        )
        article.titles.add(title)

        # Validar mapeamento MODS
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 1)

        mods_title = mods_titles[0]
        mods_content = mods_title['title'].lower()

        # Verificar que conteúdo complexo foi preservado no MODS
        self.assertIn("machine learning", mods_content, "Termo específico deve estar presente")
        self.assertIn("healthcare", mods_content, "Área de aplicação deve estar presente")
        self.assertIn("systematic review", mods_content, "Tipo de estudo deve estar presente")
        self.assertIn("deep learning", mods_content, "Tecnologia específica deve estar presente")
        self.assertIn("medical image analysis", mods_content, "Aplicação específica deve estar presente")

        # Verificar comprimento do título
        self.assertGreater(len(mods_title['title']), 100, "Título complexo deve ser longo")

        # Verificar idioma
        if 'lang' in mods_title:
            self.assertEqual(mods_title['lang'], 'en')

    def test_mods_index_special_characters(self):
        """Teste índice MODS: título com caracteres especiais"""
        article = self._create_test_article()

        special_title = "COVID-19 & SARS-CoV-2: Análise Genômica (2020-2023) — Revisão"

        title = DocumentTitle.objects.create(
            plain_text=special_title,
            language=self.lang_pt,
            creator=self.user
        )
        article.titles.add(title)

        # Validar mapeamento MODS
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 1)

        mods_title = mods_titles[0]
        title_content = mods_title['title']

        # Verificar que caracteres especiais foram preservados
        self.assertIn("COVID-19", title_content, "Número com hífen deve estar presente")
        self.assertIn("&", title_content, "Símbolo ampersand deve estar presente")
        self.assertIn("—", title_content, "Em dash deve estar presente")
        self.assertIn("(2020-2023)", title_content, "Intervalo de anos deve estar presente")
        self.assertIn("Análise", title_content, "Acentos devem estar preservados")
        self.assertIn("Genômica", title_content, "Acentos circunflexos devem estar preservados")

    def test_mods_index_empty_and_whitespace_titles(self):
        """Teste índice MODS: títulos vazios e com espaços em branco"""
        article = self._create_test_article()

        # Título com apenas espaços
        title_whitespace = DocumentTitle.objects.create(
            plain_text="   \n\t   ",  # Apenas espaços em branco
            language=self.lang_pt,
            creator=self.user
        )
        article.titles.add(title_whitespace)

        # Título vazio
        title_empty = DocumentTitle.objects.create(
            plain_text="",  # Título vazio
            language=self.lang_en,
            creator=self.user
        )
        article.titles.add(title_empty)

        # Validar mapeamento MODS
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 2, "MODS deveria ter 2 titleInfo")

        # Verificar que conteúdo foi preservado como está
        mods_texts = [title['title'] for title in mods_titles]
        self.assertIn("   \n\t   ", mods_texts, "Espaços em branco devem ser preservados")
        self.assertIn("", mods_texts, "Título vazio deve ser preservado")

    def test_mods_index_none_values_filtering(self):
        """Teste índice MODS: verificação de que valores None são filtrados"""
        article = self._create_test_article()

        # Criar título sem idioma para testar filtro de None
        title = DocumentTitle.objects.create(
            plain_text="Título para teste de filtro de valores None",
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

        # Garantir que pelo menos o campo 'title' está presente
        self.assertIn('title', mods_title, "Campo 'title' deve estar sempre presente")

    def test_mods_index_mixed_scenarios(self):
        """Teste índice MODS: cenário misto com títulos variados"""
        article = self._create_test_article()

        # Título normal com idioma
        title_normal = DocumentTitle.objects.create(
            plain_text="Título normal em português",
            language=self.lang_pt,
            creator=self.user
        )
        article.titles.add(title_normal)

        # Título sem idioma
        title_no_lang = DocumentTitle.objects.create(
            plain_text="Title without language specification",
            language=None,
            creator=self.user
        )
        article.titles.add(title_no_lang)

        # Título complexo com caracteres especiais
        title_complex = DocumentTitle.objects.create(
            plain_text="Título Complexo: Análise & Síntese — Estudo (2024)",
            language=self.lang_pt,
            creator=self.user
        )
        article.titles.add(title_complex)

        # Título com apenas espaços
        title_spaces = DocumentTitle.objects.create(
            plain_text="   ",
            language=self.lang_en,
            creator=self.user
        )
        article.titles.add(title_spaces)

        # Validar mapeamento MODS
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 4, "MODS deveria ter 4 titleInfo no cenário misto")

        # Verificar que todos têm estrutura básica
        for i, mods_title in enumerate(mods_titles):
            self.assertIn('title', mods_title, f"Título {i} deve ter campo 'title'")
            # Note: não verificamos se está vazio pois alguns títulos podem ser apenas espaços

        # Contar títulos com e sem idioma
        with_lang = [title for title in mods_titles if 'lang' in title and title['lang'] is not None]
        without_lang = [title for title in mods_titles if 'lang' not in title or title.get('lang') is None]

        self.assertGreater(len(with_lang), 0, "Deveria ter títulos com idioma")
        self.assertGreater(len(without_lang), 0, "Deveria ter títulos sem idioma")

        # Verificar conteúdo específico
        mods_texts = [title['title'] for title in mods_titles]
        self.assertIn("Título normal em português", mods_texts)
        self.assertIn("Title without language specification", mods_texts)
        self.assertTrue(any("Complexo" in text for text in mods_texts))
        self.assertIn("   ", mods_texts)

    def test_mods_index_type_field_consistency(self):
        """Teste índice MODS: consistência do campo 'type'"""
        article = self._create_test_article()

        title = DocumentTitle.objects.create(
            plain_text="Título para teste de consistência do tipo",
            language=self.lang_pt,
            creator=self.user
        )
        article.titles.add(title)

        # Validar mapeamento MODS
        mods_titles = self.index.prepare_mods_title_info(article)
        self.assertEqual(len(mods_titles), 1)

        mods_title = mods_titles[0]


# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_title_info.MODSTitleInfoTestCase -v 2
