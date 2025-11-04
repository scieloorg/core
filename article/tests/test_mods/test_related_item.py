import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model

from article.models import Article, ArticleFormat
from article.search_indexes import ArticleOAIMODSIndex
from collection.models import Collection
from core.models import Language
from doi.models import DOI
from issue.models import Issue
from journal.models import Journal, OfficialJournal, SciELOJournal
from location.models import Location, City, State, Country

User = get_user_model()


class MODSRelatedItemTestCase(TestCase):
    """
    Testes unitários otimizados para elemento relatedItem MODS
    Testa relacionamentos e estruturas do ecossistema SciELO
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
        cls.language_pt = Language.objects.create(
            name="Portuguese",
            code2="pt",
            creator=cls.user
        )

        cls.language_en = Language.objects.create(
            name="English",
            code2="en",
            creator=cls.user
        )

        # Criar localização base
        cls.country_br = Country.objects.create(
            name="Brasil",
            acronym="BR",
            acron3="BRA",
            creator=cls.user
        )

        cls.state_sp = State.objects.create(
            name="São Paulo",
            acronym="SP",
            creator=cls.user
        )

        cls.city_sp = City.objects.create(
            name="São Paulo",
            creator=cls.user
        )

        cls.location = Location.objects.create(
            country=cls.country_br,
            state=cls.state_sp,
            city=cls.city_sp,
            creator=cls.user
        )

        # Criar coleção
        cls.collection_scl = Collection.objects.create(
            acron3="scl",
            acron2="br",
            code="001",
            domain="www.scielo.br",
            main_name="SciELO Brasil",
            collection_type="journals",
            is_active=True,
            creator=cls.user
        )

        # Criar journals oficiais para relacionamentos
        cls.old_official_journal = OfficialJournal.objects.create(
            title="Revista Antiga de Medicina",
            issn_print="0100-9999",
            creator=cls.user
        )

        cls.new_official_journal = OfficialJournal.objects.create(
            title="Nova Revista de Medicina",
            issn_print="0100-8888",
            creator=cls.user
        )

        cls.official_journal = OfficialJournal.objects.create(
            title="Revista Brasileira de Medicina",
            issn_print="0100-1234",
            issn_electronic="1678-5678",
            issnl="0100-1234",
            new_title=cls.new_official_journal,
            creator=cls.user
        )

        # Configurar relacionamentos de títulos
        cls.official_journal.old_title.add(cls.old_official_journal)

        # Criar journal
        cls.journal = Journal.objects.create(
            official=cls.official_journal,
            title="Revista Brasileira de Medicina",
            creator=cls.user
        )

        # Criar SciELO Journal
        cls.scielo_journal = SciELOJournal.objects.create(
            collection=cls.collection_scl,
            journal=cls.journal,
            journal_acron="rbm",
            issn_scielo="0100-1234",
            creator=cls.user
        )

        # Criar issue
        cls.issue = Issue.objects.create(
            journal=cls.journal,
            volume="10",
            number="2",
            supplement="1",
            year="2024",
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
            'pid_v2': f'S0100-12342024000200001',
            'article_type': 'research-article',
            'journal': self.journal,
            'issue': self.issue,
            'pub_date_year': '2024',
            'creator': self.user
        }
        defaults.update(kwargs)

        article = Article.objects.create(**defaults)
        article.languages.add(self.language_pt)
        return article

    def _create_test_doi(self, value, language=None):
        """Helper para criar DOI de teste"""
        return DOI.objects.create(
            value=value,
            language=language or self.language_pt,
            creator=self.user
        )

    def _create_test_format(self, article, format_name, valid=True):
        """Helper para criar ArticleFormat de teste"""
        return ArticleFormat.objects.create(
            article=article,
            format_name=format_name,
            version=1,
            valid=valid,
            creator=self.user
        )

    def test_related_item_no_relationships(self):
        """Teste: artigo sem relacionamentos"""
        article = self._create_test_article(journal=None, issue=None)

        related_items = self.index.prepare_mods_related_item(article)

        self.assertIsInstance(related_items, list)
        self.assertEqual(len(related_items), 0)

    def test_related_item_host_basic_structure(self):
        """Teste: relacionamento HOST básico (journal/issue)"""
        article = self._create_test_article()

        related_items = self.index.prepare_mods_related_item(article)

        # Deve ter pelo menos 1 item HOST
        host_items = [item for item in related_items if item.get('type') == 'host']
        self.assertGreaterEqual(len(host_items), 1)

        host_item = host_items[0]

        # Verificar estrutura HOST
        self.assertEqual(host_item['displayLabel'], 'Published in')
        self.assertIn('titleInfo', host_item)
        self.assertEqual(host_item['titleInfo']['title'], 'Revista Brasileira de Medicina')

        # Verificar part details
        self.assertIn('part', host_item)
        part = host_item['part']
        self.assertIn('detail', part)

        # Verificar detalhes do fascículo
        details = part['detail']
        detail_types = {detail['type']: detail['number'] for detail in details}

        self.assertEqual(detail_types.get('volume'), '10')
        self.assertEqual(detail_types.get('issue'), '2')
        self.assertEqual(detail_types.get('supplement'), '1')
        self.assertEqual(part.get('date'), '2024')

    def test_related_item_host_with_issns(self):
        """Teste: HOST com ISSNs estruturados"""
        article = self._create_test_article()

        related_items = self.index.prepare_mods_related_item(article)
        host_items = [item for item in related_items if item.get('type') == 'host']

        self.assertGreater(len(host_items), 0)
        host_item = host_items[0]

        # Verificar ISSNs
        self.assertIn('identifier', host_item)
        identifiers = host_item['identifier']

        # Categorizar identificadores
        issn_categories = {
            'Print ISSN': '0100-1234',
            'Electronic ISSN': '1678-5678',
        }

        for display_label, expected_value in issn_categories.items():
            issn_items = [id_item for id_item in identifiers
                          if id_item.get('displayLabel') == display_label]
            self.assertEqual(len(issn_items), 1)
            self.assertEqual(issn_items[0]['text'], expected_value)

        # Verificar ISSNL
        issnl_items = [id_item for id_item in identifiers if id_item.get('type') == 'issnl']
        self.assertEqual(len(issnl_items), 1)
        self.assertEqual(issnl_items[0]['text'], '0100-1234')

    def test_related_item_other_formats(self):
        """Teste: outros formatos (ArticleFormat)"""
        article = self._create_test_article()

        format_test_cases = [
            ('crossref', 'CROSSREF format', 'CrossRef XML'),
            ('pubmed', 'PUBMED format', 'PubMed XML'),
            ('pmc', 'PMC format', 'PMC XML'),
        ]

        # Criar formatos
        for format_name, expected_display, expected_genre in format_test_cases:
            self._create_test_format(article, format_name)

        related_items = self.index.prepare_mods_related_item(article)

        # Filtrar apenas formatos específicos
        format_items = [
            item for item in related_items
            if item.get('type') == 'otherFormat' and 'format' in item.get('displayLabel', '').lower()
        ]

        self.assertEqual(len(format_items), 3)

        # Verificar cada formato
        for format_name, expected_display, expected_genre in format_test_cases:
            with self.subTest(format_name=format_name):
                format_item = next(
                    (item for item in format_items if expected_display in item['displayLabel']),
                    None
                )
                self.assertIsNotNone(format_item)
                self.assertEqual(format_item.get('genre'), expected_genre)

    def test_related_item_doi_versions(self):
        """Teste: outras versões via DOI com idiomas"""
        article = self._create_test_article()

        doi_test_cases = [
            ("10.1590/S0100-12342024000200001", self.language_pt, 'pt'),
            ("10.1590/S0100-12342024000200002", self.language_en, 'en'),
        ]

        # Criar DOIs
        for doi_value, language, expected_lang in doi_test_cases:
            doi = self._create_test_doi(doi_value, language)
            article.doi.add(doi)

        related_items = self.index.prepare_mods_related_item(article)

        # Filtrar DOIs
        doi_items = [
            item for item in related_items
            if item.get('type') == 'otherVersion' and 'DOI' in item.get('displayLabel', '')
        ]

        self.assertEqual(len(doi_items), 2)

        # Verificar cada DOI
        for doi_value, language, expected_lang in doi_test_cases:
            with self.subTest(doi=doi_value):
                doi_item = next(
                    (item for item in doi_items
                     if doi_value in item.get('xlink:href', '')),
                    None
                )
                self.assertIsNotNone(doi_item)
                self.assertEqual(doi_item['xlink:href'], f'https://doi.org/{doi_value}')
                self.assertEqual(doi_item.get('lang'), expected_lang)

    def test_related_item_preceding_succeeding_titles(self):
        """Teste: títulos precedentes e sucessores"""
        article = self._create_test_article()

        related_items = self.index.prepare_mods_related_item(article)

        title_relationships = [
            ('preceding', 'Previous journal title', 'Revista Antiga de Medicina'),
            ('succeeding', 'New journal title', 'Nova Revista de Medicina'),
        ]

        for relation_type, expected_display, expected_title in title_relationships:
            with self.subTest(relation=relation_type):
                items = [item for item in related_items if item.get('type') == relation_type]
                self.assertEqual(len(items), 1)

                item = items[0]
                self.assertEqual(item['displayLabel'], expected_display)
                self.assertEqual(item['titleInfo']['title'], expected_title)

    def test_related_item_format_validation(self):
        """Teste: validação de formatos (válidos vs inválidos)"""
        article = self._create_test_article()

        # Criar formato válido e inválido
        self._create_test_format(article, 'crossref', valid=True)
        self._create_test_format(article, 'invalid_format', valid=False)

        related_items = self.index.prepare_mods_related_item(article)

        # Filtrar formatos
        format_items = [
            item for item in related_items
            if item.get('type') == 'otherFormat' and 'format' in item.get('displayLabel', '').lower()
        ]

        format_names = [item['displayLabel'] for item in format_items]
        self.assertIn('CROSSREF format', format_names)
        self.assertNotIn('INVALID_FORMAT format', format_names)

    def test_related_item_edge_cases_handling(self):
        """Teste: casos extremos e tratamento de erros"""
        edge_cases = [
            ('empty_doi', lambda article: article.doi.add(self._create_test_doi(""))),
            ('no_journal_issue', lambda article: None),  # Artigo criado sem journal/issue
        ]

        for case_name, setup_func in edge_cases:
            with self.subTest(case=case_name):
                if case_name == 'no_journal_issue':
                    article = self._create_test_article(journal=None, issue=None)
                else:
                    article = self._create_test_article()
                    if setup_func:
                        setup_func(article)

                related_items = self.index.prepare_mods_related_item(article)

                # Deve sempre retornar lista válida
                self.assertIsInstance(related_items, list)

                if case_name == 'empty_doi':
                    # DOI vazio não deve aparecer
                    doi_items = [
                        item for item in related_items
                        if item.get('type') == 'otherVersion' and 'DOI' in item.get('displayLabel', '')
                    ]
                    self.assertEqual(len(doi_items), 0)

                elif case_name == 'no_journal_issue':
                    # Não deve ter HOST ou relacionamentos de título
                    host_items = [item for item in related_items if item.get('type') == 'host']
                    title_items = [item for item in related_items
                                   if item.get('type') in ['preceding', 'succeeding']]
                    self.assertEqual(len(host_items), 0)
                    self.assertEqual(len(title_items), 0)

    def test_related_item_complete_scenario(self):
        """Teste: cenário completo com múltiplos relacionamentos"""
        article = self._create_test_article()

        # Adicionar DOI
        doi = self._create_test_doi("10.1590/test.doi")
        article.doi.add(doi)

        # Adicionar formato
        self._create_test_format(article, 'crossref')

        related_items = self.index.prepare_mods_related_item(article)

        # Verificar tipos presentes
        item_types = [item['type'] for item in related_items]
        expected_types = ['host', 'otherVersion', 'otherFormat', 'preceding', 'succeeding']

        for expected_type in expected_types:
            self.assertIn(expected_type, item_types, f"Tipo '{expected_type}' não encontrado")

        # Verificar quantidade mínima
        self.assertGreaterEqual(len(related_items), 5)

    def test_related_item_structure_consistency(self):
        """Teste: consistência da estrutura relatedItem"""
        article = self._create_test_article()

        # Adicionar diferentes tipos de relacionamentos
        doi = self._create_test_doi("10.1590/test.consistency")
        article.doi.add(doi)
        self._create_test_format(article, 'pubmed')

        related_items = self.index.prepare_mods_related_item(article)

        # Validar estrutura de cada item
        for item in related_items:
            self.assertIsInstance(item, dict)
            self.assertIn('type', item)
            self.assertIn('displayLabel', item)

            # Validar estruturas específicas por tipo
            if item['type'] == 'host':
                self.assertIn('titleInfo', item)
                self.assertIn('identifier', item)
                self.assertIn('part', item)
            elif item['type'] == 'otherVersion':
                if 'DOI' in item['displayLabel']:
                    self.assertIn('xlink:href', item)
            elif item['type'] == 'otherFormat':
                if 'format' in item['displayLabel'].lower():
                    self.assertIn('genre', item)
            elif item['type'] in ['preceding', 'succeeding']:
                self.assertIn('titleInfo', item)

    def test_related_item_safe_collections_handling(self):
        """Teste: tratamento seguro de collections"""
        test_cases = [
            ('normal_article', lambda: self._create_test_article()),
            ('article_none', lambda: None),
            ('article_no_journal', lambda: self._create_test_article(journal=None)),
        ]

        for case_name, article_creator in test_cases:
            with self.subTest(case=case_name):
                if case_name == 'article_none':
                    collections = self.index._safe_get_collections(None)
                    self.assertEqual(collections, [])
                else:
                    article = article_creator()
                    collections = self.index._safe_get_collections(article)
                    self.assertIsInstance(collections, list)

    def test_related_item_scielo_urls_structure(self):
        """Teste: estrutura de URLs SciELO quando presentes"""
        article = self._create_test_article()

        related_items = self.index.prepare_mods_related_item(article)

        # Verificar URLs SciELO se existirem
        scielo_url_items = [
            item for item in related_items
            if 'SciELO' in item.get('displayLabel', '') and 'xlink:href' in item
        ]

        # Se existem URLs SciELO, verificar estrutura
        for item in scielo_url_items:
            self.assertIn('xlink:href', item)
            self.assertIn('displayLabel', item)
            self.assertIn(item.get('type'), ['otherVersion', 'otherFormat'])

    def test_related_item_multiple_relationships_priority(self):
        """Teste: prioridade e ordenação de relacionamentos múltiplos"""
        article = self._create_test_article()

        # Adicionar múltiplos DOIs e formatos
        dois = [
            self._create_test_doi("10.1590/first.doi", self.language_pt),
            self._create_test_doi("10.1590/second.doi", self.language_en),
        ]

        for doi in dois:
            article.doi.add(doi)

        formats = ['crossref', 'pubmed', 'pmc']
        for format_name in formats:
            self._create_test_format(article, format_name)

        related_items = self.index.prepare_mods_related_item(article)

        # Verificar que todos os relacionamentos estão presentes
        doi_items = [item for item in related_items
                     if item.get('type') == 'otherVersion' and 'DOI' in item.get('displayLabel', '')]
        format_items = [item for item in related_items
                        if item.get('type') == 'otherFormat' and 'format' in item.get('displayLabel', '').lower()]

        self.assertEqual(len(doi_items), 2)
        self.assertEqual(len(format_items), 3)

        # Verificar que HOST sempre está presente quando há journal/issue
        host_items = [item for item in related_items if item.get('type') == 'host']
        self.assertGreaterEqual(len(host_items), 1)

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_related_item.MODSRelatedItemTestCase --parallel 2 -v 2
