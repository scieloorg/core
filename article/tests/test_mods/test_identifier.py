import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from article.models import Article
from article.search_indexes import ArticleOAIMODSIndex
from collection.models import Collection, CollectionName
from core.models import Language
from doi.models import DOI
from issue.models import Issue
from journal.models import Journal, OfficialJournal, SciELOJournal
from location.models import Location, City, State, Country

User = get_user_model()


class MODSIdentifierTestCase(TestCase):
    """
    Testes unitários otimizados para elemento identifier MODS
    Testa todos os tipos de identificadores do ecossistema SciELO
    """

    @classmethod
    def setUpTestData(cls):
        """Dados compartilhados entre testes para melhor performance"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

        # Criar idioma uma vez
        cls.language_pt = Language.objects.create(
            name="Portuguese",
            code2="pt",
            creator=cls.user
        )

        # Criar localização mínima uma vez
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

        # Criar coleções
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

        cls.collection_mex = Collection.objects.create(
            acron3="mex",
            code="002",
            domain="www.scielo.org.mx",
            main_name="SciELO México",
            collection_type="journals",
            is_active=True,
            creator=cls.user
        )

        # Criar journal oficial
        cls.official_journal = OfficialJournal.objects.create(
            title="Revista Brasileira de Medicina",
            issn_print="0100-1234",
            issn_electronic="1678-5678",
            issnl="0100-1234",
            creator=cls.user
        )

        # Criar journal
        cls.journal = Journal.objects.create(
            official=cls.official_journal,
            title="Revista Brasileira de Medicina",
            creator=cls.user
        )

        # Criar SciELO Journals
        cls.scielo_journal_scl = SciELOJournal.objects.create(
            collection=cls.collection_scl,
            journal=cls.journal,
            journal_acron="rbm",
            issn_scielo="0100-1234",
            creator=cls.user
        )

        cls.scielo_journal_mex = SciELOJournal.objects.create(
            collection=cls.collection_mex,
            journal=cls.journal,
            journal_acron="rbm-mx",
            issn_scielo="0100-1234",
            creator=cls.user
        )

        # Criar issue
        cls.issue = Issue.objects.create(
            journal=cls.journal,
            volume="10",
            number="2",
            year="2024",
            issue_pid_suffix="0001",
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

    def test_identifier_no_identifiers(self):
        """Teste: artigo sem identificadores específicos"""
        article = Article.objects.create(
            article_type='research-article',
            creator=self.user
        )

        mods_identifiers = self.index.prepare_mods_identifier(article)

        self.assertEqual(len(mods_identifiers), 0)

    def test_identifier_basic_pids(self):
        """Teste: PIDs SciELO básicos"""
        article = self._create_test_article()

        mods_identifiers = self.index.prepare_mods_identifier(article)

        # Deve ter pelo menos PIDs v2, v3 e package name
        self.assertGreaterEqual(len(mods_identifiers), 3)

        # Verificar PID v3
        pid_v3 = next((i for i in mods_identifiers
                       if i.get('displayLabel') == 'SciELO PID v3'), None)
        self.assertIsNotNone(pid_v3)
        self.assertEqual(pid_v3['type'], 'local')
        self.assertEqual(pid_v3['text'], article.pid_v3)

        # Verificar PID v2
        pid_v2 = next((i for i in mods_identifiers
                       if i.get('displayLabel') == 'SciELO PID v2'), None)
        self.assertIsNotNone(pid_v2)
        self.assertEqual(pid_v2['type'], 'local')
        self.assertEqual(pid_v2['text'], article.pid_v2)

    def test_identifier_doi_validation(self):
        """Teste: validação de DOIs válidos e inválidos"""
        doi_test_cases = [
            ("10.1590/S0100-12342024000200001", True),
            ("invalid-doi-format", False),
            ("10.123/too-short-prefix", False),
            ("10.1234/valid-doi", True),
        ]

        for doi_value, is_valid in doi_test_cases:
            with self.subTest(doi=doi_value, expected_valid=is_valid):
                article = self._create_test_article()
                test_doi = self._create_test_doi(doi_value)
                article.doi.add(test_doi)

                mods_identifiers = self.index.prepare_mods_identifier(article)
                doi_identifiers = [i for i in mods_identifiers if i.get('type') == 'doi']

                self.assertEqual(len(doi_identifiers), 1)
                doi_id = doi_identifiers[0]
                self.assertEqual(doi_id['text'], doi_value)

                if is_valid:
                    self.assertNotIn('invalid', doi_id)
                else:
                    self.assertEqual(doi_id['invalid'], 'yes')

    def test_identifier_multiple_dois(self):
        """Teste: múltiplos DOIs (válido e inválido)"""
        article = self._create_test_article()

        valid_doi = self._create_test_doi("10.1590/S0100-12342024000200001")
        invalid_doi = self._create_test_doi("10.123/invalid")
        article.doi.add(valid_doi, invalid_doi)

        mods_identifiers = self.index.prepare_mods_identifier(article)
        doi_identifiers = [i for i in mods_identifiers if i.get('type') == 'doi']

        self.assertEqual(len(doi_identifiers), 2)

        # Verificar DOI válido
        valid_dois = [i for i in doi_identifiers if 'invalid' not in i]
        self.assertEqual(len(valid_dois), 1)
        self.assertEqual(valid_dois[0]['text'], "10.1590/S0100-12342024000200001")

        # Verificar DOI inválido
        invalid_dois = [i for i in doi_identifiers if 'invalid' in i]
        self.assertEqual(len(invalid_dois), 1)
        self.assertEqual(invalid_dois[0]['text'], "10.123/invalid")

    def test_identifier_journal_issns(self):
        """Teste: ISSNs do journal"""
        article = self._create_test_article()

        mods_identifiers = self.index.prepare_mods_identifier(article)

        # Verificar ISSN Print
        print_issn = next((i for i in mods_identifiers
                           if i.get('displayLabel') == 'Print ISSN'), None)
        self.assertIsNotNone(print_issn)
        self.assertEqual(print_issn['type'], 'issn')
        self.assertEqual(print_issn['text'], '0100-1234')

        # Verificar ISSN Electronic
        electronic_issn = next((i for i in mods_identifiers
                                if i.get('displayLabel') == 'Electronic ISSN'), None)
        self.assertIsNotNone(electronic_issn)
        self.assertEqual(electronic_issn['type'], 'issn')
        self.assertEqual(electronic_issn['text'], '1678-5678')

        # Verificar ISSNL
        issnl = next((i for i in mods_identifiers if i.get('type') == 'issnl'), None)
        self.assertIsNotNone(issnl)
        self.assertEqual(issnl['text'], '0100-1234')

    def test_identifier_collection_identifiers(self):
        """Teste: identificadores de coleção"""
        article = self._create_test_article()

        mods_identifiers = self.index.prepare_mods_identifier(article)

        # Verificar Collection Acronym
        collection_acron = next((i for i in mods_identifiers
                                 if i.get('displayLabel') == 'Collection Acronym'), None)
        self.assertIsNotNone(collection_acron)
        self.assertEqual(collection_acron['type'], 'local')
        self.assertEqual(collection_acron['text'], 'scl')

        # Verificar Collection Code
        collection_code = next((i for i in mods_identifiers
                                if i.get('displayLabel') == 'Collection Code'), None)
        self.assertIsNotNone(collection_code)
        self.assertEqual(collection_code['type'], 'local')
        self.assertEqual(collection_code['text'], '001')

    def test_identifier_scielo_journal_identifiers(self):
        """Teste: identificadores do SciELO Journal"""
        article = self._create_test_article()

        mods_identifiers = self.index.prepare_mods_identifier(article)

        # Verificar Journal Acronym
        journal_acron = next((i for i in mods_identifiers
                              if 'Journal Acronym' in i.get('displayLabel', '')), None)
        self.assertIsNotNone(journal_acron)
        self.assertEqual(journal_acron['type'], 'local')
        self.assertEqual(journal_acron['text'], 'rbm')
        self.assertIn('(scl)', journal_acron['displayLabel'])

    def test_identifier_issue_identifiers(self):
        """Teste: identificadores do Issue"""
        article = self._create_test_article()

        mods_identifiers = self.index.prepare_mods_identifier(article)

        # Verificar Issue PID Suffix
        issue_pid = next((i for i in mods_identifiers
                          if i.get('displayLabel') == 'Issue PID Suffix'), None)
        self.assertIsNotNone(issue_pid)
        self.assertEqual(issue_pid['type'], 'local')
        self.assertEqual(issue_pid['text'], '0001')

    def test_identifier_canonical_urls(self):
        """Teste: URLs canônicas"""
        article = self._create_test_article()

        mods_identifiers = self.index.prepare_mods_identifier(article)

        # Verificar URL canônica
        canonical_url = next((i for i in mods_identifiers
                              if 'Canonical URL' in i.get('displayLabel', '')), None)
        self.assertIsNotNone(canonical_url)
        self.assertEqual(canonical_url['type'], 'uri')
        expected_url = f"https://www.scielo.br/scielo.php?script=sci_arttext&pid={article.pid_v2}"
        self.assertEqual(canonical_url['text'], expected_url)

    def test_identifier_article_without_journal(self):
        """Teste: artigo sem journal"""
        article = Article.objects.create(
            pid_v2="S0000-00002024000100001",
            pid_v3=f'test-{uuid.uuid4().hex[:12]}',
            sps_pkg_name=f'test-{uuid.uuid4().hex[:12]}',
            article_type='research-article',
            creator=self.user
        )

        mods_identifiers = self.index.prepare_mods_identifier(article)

        # Deve ter apenas PIDs próprios do artigo
        self.assertGreaterEqual(len(mods_identifiers), 3)

        # Não deve ter ISSNs
        issn_identifiers = [i for i in mods_identifiers if i.get('type') == 'issn']
        self.assertEqual(len(issn_identifiers), 0)

    def test_identifier_article_without_issue(self):
        """Teste: artigo sem issue"""
        article = self._create_test_article(issue=None)

        mods_identifiers = self.index.prepare_mods_identifier(article)

        # Não deve ter Issue PID Suffix
        issue_identifiers = [i for i in mods_identifiers
                             if 'Issue PID' in i.get('displayLabel', '')]
        self.assertEqual(len(issue_identifiers), 0)

    def test_identifier_multiple_collections_scenario(self):
        """Teste: journal em múltiplas coleções"""
        article = self._create_test_article()
        mods_identifiers = self.index.prepare_mods_identifier(article)

        # Verificar identificadores de ambas as coleções
        collection_identifiers = [i for i in mods_identifiers
                                  if 'Collection' in i.get('displayLabel', '')]
        self.assertGreaterEqual(len(collection_identifiers), 2)

        # Verificar journal acronyms específicos por coleção
        journal_acron_identifiers = [i for i in mods_identifiers
                                     if 'Journal Acronym' in i.get('displayLabel', '')]
        self.assertGreaterEqual(len(journal_acron_identifiers), 2)

        # Verificar conteúdo específico
        acron_texts = [i['text'] for i in journal_acron_identifiers]
        self.assertIn('rbm', acron_texts)
        self.assertIn('rbm-mx', acron_texts)

    def test_identifier_empty_values_handling(self):
        """Teste: tratamento de valores vazios"""
        article = Article.objects.create(
            pid_v3=f'test-{uuid.uuid4().hex[:12]}',
            article_type='research-article',
            creator=self.user
        )

        mods_identifiers = self.index.prepare_mods_identifier(article)

        # Deve ter apenas PID v3
        self.assertEqual(len(mods_identifiers), 1)

        pid_v3_id = mods_identifiers[0]
        self.assertEqual(pid_v3_id['displayLabel'], 'SciELO PID v3')
        self.assertEqual(pid_v3_id['text'], article.pid_v3)

    def test_identifier_complete_scenario(self):
        """Teste: cenário completo com todos os identificadores"""
        article = self._create_test_article()

        # Adicionar DOI válido
        valid_doi = self._create_test_doi("10.1590/S0100-12342024000200001")
        article.doi.add(valid_doi)

        mods_identifiers = self.index.prepare_mods_identifier(article)

        # Verificar tipos de identificadores presentes
        types_present = set(i.get('type') for i in mods_identifiers)
        expected_types = {'doi', 'issn', 'issnl', 'local', 'uri'}

        for expected_type in expected_types:
            self.assertIn(expected_type, types_present,
                          f"Tipo '{expected_type}' não encontrado nos identificadores")

        # Verificar quantidade mínima de identificadores
        self.assertGreaterEqual(len(mods_identifiers), 10)

        # Verificar ordem: DOIs primeiro, depois outros
        doi_positions = [i for i, item in enumerate(mods_identifiers)
                         if item.get('type') == 'doi']
        uri_positions = [i for i, item in enumerate(mods_identifiers)
                         if item.get('type') == 'uri']

        if doi_positions and uri_positions:
            self.assertLess(doi_positions[0], uri_positions[0],
                            "DOIs devem aparecer antes das URIs")

    def test_doi_validation_edge_cases(self):
        """Teste: validação de DOI - casos extremos"""
        doi_test_cases = [
            ("10.1234/valid-doi", True),
            ("10.12345/another.valid-doi_123", True),
            ("10.123/too-short-prefix", False),
            ("11.1234/wrong-prefix", False),
            ("10.1234/", False),
            ("10.1234", False),
            ("not-a-doi", False),
            ("", False),
            ("   10.1234/with-spaces   ", True),
        ]

        for doi_value, should_be_valid in doi_test_cases:
            with self.subTest(doi=doi_value, expected_valid=should_be_valid):
                is_valid = self.index._is_valid_doi(doi_value)
                self.assertEqual(is_valid, should_be_valid,
                                 f"DOI '{doi_value}' validação incorreta")

    def test_identifier_priority_and_order(self):
        """Teste: prioridade e ordem dos identificadores"""
        article = self._create_test_article()

        # Adicionar múltiplos DOIs
        doi1 = self._create_test_doi("10.1590/S0100-12342024000200001")
        doi2 = self._create_test_doi("10.1590/S0100-12342024000200002")
        article.doi.add(doi1, doi2)

        mods_identifiers = self.index.prepare_mods_identifier(article)

        # DOIs devem aparecer primeiro
        first_items = mods_identifiers[:3]
        doi_first = [i for i in first_items if i.get('type') == 'doi']
        self.assertGreaterEqual(len(doi_first), 1)

        # PIDs devem aparecer antes de ISSNs
        pid_positions = [i for i, item in enumerate(mods_identifiers)
                         if 'PID' in item.get('displayLabel', '')]
        issn_positions = [i for i, item in enumerate(mods_identifiers)
                          if item.get('type') == 'issn']

        if pid_positions and issn_positions:
            self.assertLess(min(pid_positions), min(issn_positions))

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_identifier.MODSIdentifierTestCase --parallel 2 -v 2
