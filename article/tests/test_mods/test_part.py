import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model

from article.models import Article
from article.search_indexes import ArticleOAIMODSIndex
from core.models import Language
from issue.models import Issue
from journal.models import Journal, OfficialJournal

User = get_user_model()


class MODSPartTestCase(TestCase):
    """
    Testes unitários focados no índice MODS para elemento part
    Baseado nos exemplos MODS reais fornecidos
    """

    @classmethod
    def setUpTestData(cls):
        """Dados compartilhados entre testes para melhor performance"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

        cls.language_pt = Language.objects.create(
            name="Portuguese",
            code2="pt",
            creator=cls.user
        )

        cls.official_journal = OfficialJournal.objects.create(
            title="Revista Brasileira de Medicina",
            issn_print="0100-1234",
            creator=cls.user
        )

        cls.journal = Journal.objects.create(
            official=cls.official_journal,
            title="Revista Brasileira de Medicina",
            creator=cls.user
        )

        cls.issue = Issue.objects.create(
            journal=cls.journal,
            volume="10",
            number="2",
            year="2024",
            creator=cls.user
        )

    def setUp(self):
        """Configuração específica por teste"""
        self.index = ArticleOAIMODSIndex()

    def tearDown(self):
        """Limpeza mínima - TestCase faz rollback automático"""
        pass

    def _create_test_article(self, **kwargs):
        """Helper otimizado para criar artigo de teste"""
        defaults = {
            'pid_v3': f'test-{uuid.uuid4().hex[:8]}',  # UUID menor
            'article_type': 'research-article',
            'journal': self.journal,
            'issue': self.issue,
            'creator': self.user
        }
        defaults.update(kwargs)

        return Article.objects.create(**defaults)

    def test_part_no_pagination_info(self):
        """Teste MODS part: artigo sem informações de paginação"""
        article = self._create_test_article()

        parts = self.index.prepare_mods_part(article)

        # Deve retornar lista vazia
        self.assertIsInstance(parts, list)
        self.assertEqual(len(parts), 0)

    def test_part_extent_with_start_and_end_pages(self):
        """Teste MODS part: extent com páginas inicial e final (baseado nos exemplos)"""
        article = self._create_test_article(
            first_page="43",
            last_page="70"
        )

        parts = self.index.prepare_mods_part(article)

        self.assertEqual(len(parts), 1)
        part = parts[0]

        # Verificar estrutura extent baseada nos exemplos MODS
        self.assertIn('extent', part)
        extent = part['extent']

        # Verificar estrutura conforme exemplos: <extent unit="page"><start>43</start><end>70</end></extent>
        self.assertEqual(extent['unit'], 'page')
        self.assertEqual(extent['start'], '43')
        self.assertEqual(extent['end'], '70')

    def test_part_extent_with_start_page_only(self):
        """Teste MODS part: extent apenas com página inicial"""
        article = self._create_test_article(
            first_page="97",
            last_page=None
        )

        parts = self.index.prepare_mods_part(article)

        self.assertEqual(len(parts), 1)
        part = parts[0]

        # Verificar extent apenas com start
        self.assertIn('extent', part)
        extent = part['extent']

        self.assertEqual(extent['unit'], 'page')
        self.assertEqual(extent['start'], '97')
        self.assertNotIn('end', extent)

    def test_part_detail_elocation_id(self):
        """Teste MODS part: detail com elocation-id"""
        article = self._create_test_article(
            elocation_id="e20240001",
            first_page=None,
            last_page=None
        )

        parts = self.index.prepare_mods_part(article)

        self.assertEqual(len(parts), 1)
        part = parts[0]

        # Verificar detail para elocation-id
        self.assertIn('detail', part)
        detail = part['detail']

        self.assertEqual(detail['type'], 'elocation-id')
        self.assertEqual(detail['number'], 'e20240001')

    def test_part_extent_priority_over_elocation(self):
        """Teste MODS part: extent tem prioridade sobre elocation-id"""
        article = self._create_test_article(
            first_page="123",
            last_page="135",
            elocation_id="e20240001"
        )

        parts = self.index.prepare_mods_part(article)

        self.assertEqual(len(parts), 1)
        part = parts[0]

        # Deve ter extent, não detail
        self.assertIn('extent', part)
        self.assertNotIn('detail', part)

        extent = part['extent']
        self.assertEqual(extent['start'], '123')
        self.assertEqual(extent['end'], '135')

    def test_part_page_numbers_as_strings(self):
        """Teste MODS part: números de página como strings"""
        article = self._create_test_article(
            first_page=100,  # Número
            last_page=105  # Número
        )

        parts = self.index.prepare_mods_part(article)

        self.assertEqual(len(parts), 1)
        part = parts[0]

        extent = part['extent']

        # Deve converter números para strings
        self.assertIsInstance(extent['start'], str)
        self.assertIsInstance(extent['end'], str)
        self.assertEqual(extent['start'], '100')
        self.assertEqual(extent['end'], '105')

    def test_part_unit_singular_page(self):
        """Teste MODS part: unit deve ser 'page' (singular) conforme exemplos"""
        article = self._create_test_article(
            first_page="1",
            last_page="10"
        )

        parts = self.index.prepare_mods_part(article)

        part = parts[0]
        extent = part['extent']

        # Verificar que é 'page' (singular), não 'pages'
        self.assertEqual(extent['unit'], 'page')

    def test_part_empty_values_handling(self):
        """Teste MODS part: tratamento de valores vazios"""
        article = self._create_test_article(
            first_page="",  # String vazia
            last_page="",  # String vazia
            elocation_id=""  # String vazia
        )

        parts = self.index.prepare_mods_part(article)

        # Não deve criar parte com valores vazios
        self.assertEqual(len(parts), 0)

    def test_part_whitespace_trimming(self):
        """Teste MODS part: remoção de espaços em branco"""
        article = self._create_test_article(
            first_page="  123  ",
            last_page="  135  "
        )

        parts = self.index.prepare_mods_part(article)

        part = parts[0]
        extent = part['extent']

        # Deve remover espaços em branco
        self.assertEqual(extent['start'], '123')
        self.assertEqual(extent['end'], '135')

    def test_part_special_page_numbers(self):
        """Teste MODS part: números de página especiais (romanos, letras)"""
        article = self._create_test_article(
            first_page="xvii",
            last_page="xxiii"
        )

        parts = self.index.prepare_mods_part(article)

        part = parts[0]
        extent = part['extent']

        # Deve aceitar números romanos
        self.assertEqual(extent['start'], 'xvii')
        self.assertEqual(extent['end'], 'xxiii')
        self.assertEqual(extent['unit'], 'page')

    def test_part_elocation_id_format_preservation(self):
        """Teste MODS part: preservação do formato do elocation-id"""
        elocation_formats = [
            "e20240001",
            "E123456",
            "art-001",
            "10.1590.001"
        ]

        for elocation in elocation_formats:
            with self.subTest(elocation=elocation):
                article = self._create_test_article(elocation_id=elocation)

                parts = self.index.prepare_mods_part(article)

                part = parts[0]
                detail = part['detail']

                self.assertEqual(detail['number'], elocation)
                self.assertEqual(detail['type'], 'elocation-id')

    def test_part_numeric_conversion_safety(self):
        """Teste MODS part: conversão segura de números para string"""
        article = self._create_test_article(
            first_page=0,  # Zero
            last_page=None  # None
        )

        parts = self.index.prepare_mods_part(article)

        # Com first_page = 0 (falsy) e last_page = None, não deve criar extent
        self.assertEqual(len(parts), 0)

    def test_part_structure_completeness(self):
        """Teste MODS part: estrutura completa conforme especificação"""
        article = self._create_test_article(
            first_page="97",
            last_page="98"
        )

        parts = self.index.prepare_mods_part(article)

        part = parts[0]

        # Verificar que retorna apenas os campos necessários, sem extras
        expected_keys = {'extent'}
        self.assertEqual(set(part.keys()), expected_keys)

        # Verificar estrutura interna do extent
        extent = part['extent']
        expected_extent_keys = {'unit', 'start', 'end'}
        self.assertEqual(set(extent.keys()), expected_extent_keys)

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_part.MODSPartTestCase --parallel 2 -v 2
