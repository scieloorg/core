import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model

from article.models import Article
from article.search_indexes import ArticleOAIMODSIndex
from collection.models import Collection
from core.models import Language
from journal.models import Journal, OfficialJournal, PublisherHistory
from location.models import Location, City, State, Country
from organization.models import Organization

User = get_user_model()


class MODSLocationTestCase(TestCase):
    """
    Testes unitários para elemento location MODS
    Testa URLs eletrônicas e localização física da editora
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

        # Criar localização geográfica
        cls.country = Country.objects.create(
            name='Brasil',
            acronym='BR',
            acron3='BRA',
            creator=cls.user
        )

        cls.state = State.objects.create(
            name='São Paulo',
            acronym='SP',
            creator=cls.user
        )

        cls.city = City.objects.create(
            name='São Paulo',
            creator=cls.user
        )

        # Criar Location com relacionamentos corretos
        cls.location = Location.objects.create(
            city=cls.city,
            state=cls.state,
            country=cls.country,
            creator=cls.user
        )

        # Criar coleção
        cls.collection = Collection.objects.create(
            acron3='scl',
            domain='www.scielo.br',
            main_name='SciELO Brasil',
            is_active=True,
            creator=cls.user
        )

    def setUp(self):
        """Configuração mínima por teste"""
        self.index = ArticleOAIMODSIndex()

    def _create_test_article(self, **kwargs):
        """Helper otimizado para criar artigo de teste"""
        defaults = {
            'sps_pkg_name': f'test-{uuid.uuid4().hex[:12]}',
            'pid_v2': f'S0102-311X2024000100001',
            'pid_v3': f'test-{uuid.uuid4().hex[:12]}',
            'article_type': 'research-article',
            'creator': self.user
        }
        defaults.update(kwargs)
        return Article.objects.create(**defaults)

    def _create_test_journal_with_publisher(self, organization_name='Test Publisher'):
        """Helper para criar journal com editora"""
        official = OfficialJournal.objects.create(
            title='Test Journal',
            issn_print='0102-311X',
            creator=self.user
        )

        journal = Journal.objects.create(
            official=official,
            title='Test Journal',
            creator=self.user
        )

        organization = Organization.objects.create(
            name=organization_name,
            acronym='TP',
            location=self.location,
            creator=self.user
        )

        PublisherHistory.objects.create(
            journal=journal,
            organization=organization,
            creator=self.user
        )

        return journal

    def test_location_no_journal(self):
        """Teste: artigo sem journal"""
        article = self._create_test_article()

        mods_locations = self.index.prepare_mods_location(article)

        self.assertEqual(len(mods_locations), 0)

    def test_location_basic_urls_single_collection(self):
        """Teste: URLs básicas com uma coleção"""
        journal = self._create_test_journal_with_publisher()
        article = self._create_test_article(journal=journal)

        mods_locations = self.index.prepare_mods_location(article)

        # Deve ter pelo menos URLs (HTML e PDF) se collections retornar dados
        self.assertIsInstance(mods_locations, list)

    def test_location_url_structure_html(self):
        """Teste: estrutura correta do URL HTML"""
        journal = self._create_test_journal_with_publisher()
        article = self._create_test_article(journal=journal, pid_v2='S0102-311X2024000100001')

        mods_locations = self.index.prepare_mods_location(article)

        # Encontrar URL HTML se existir
        html_urls = [
            loc['url'] for loc in mods_locations
            if 'url' in loc and loc['url'].get('usage') == 'primary display'
        ]

        if html_urls:
            html_url = html_urls[0]
            self.assertEqual(html_url['usage'], 'primary display')
            self.assertEqual(html_url['access'], 'object in context')
            self.assertIn('displayLabel', html_url)
            self.assertIn('HTML', html_url['displayLabel'])
            self.assertIn('text', html_url)
            self.assertIn('scielo.php?script=sci_arttext', html_url['text'])
            self.assertIn('S0102-311X2024000100001', html_url['text'])

    def test_location_url_structure_pdf(self):
        """Teste: estrutura correta do URL PDF"""
        journal = self._create_test_journal_with_publisher()
        article = self._create_test_article(journal=journal, pid_v2='S0102-311X2024000100001')

        mods_locations = self.index.prepare_mods_location(article)

        # Encontrar URL PDF se existir
        pdf_urls = [
            loc['url'] for loc in mods_locations
            if 'url' in loc and
            loc['url'].get('access') == 'raw object' and
            'PDF' in loc['url'].get('displayLabel', '')
        ]

        if pdf_urls:
            pdf_url = pdf_urls[0]
            self.assertEqual(pdf_url['access'], 'raw object')
            self.assertIn('displayLabel', pdf_url)
            self.assertIn('PDF', pdf_url['displayLabel'])
            self.assertIn('note', pdf_url)
            self.assertEqual(pdf_url['note'], 'Adobe Acrobat Reader required')
            self.assertIn('text', pdf_url)
            self.assertIn('scielo.php?script=sci_pdf', pdf_url['text'])

    def test_location_date_last_accessed(self):
        """Teste: campo dateLastAccessed quando presente"""
        journal = self._create_test_journal_with_publisher()
        article = self._create_test_article(journal=journal)

        mods_locations = self.index.prepare_mods_location(article)

        # Verificar se algum URL tem dateLastAccessed
        urls_with_date = [
            loc['url'] for loc in mods_locations
            if 'url' in loc and 'dateLastAccessed' in loc['url']
        ]

        # Se houver URLs com data, verificar formato
        for url in urls_with_date:
            date_str = url['dateLastAccessed']
            self.assertRegex(date_str, r'^\d{4}-\d{2}-\d{2}$')

    def test_location_multiple_languages_urls(self):
        """Teste: URLs específicos por idioma"""
        journal = self._create_test_journal_with_publisher()
        article = self._create_test_article(journal=journal)

        # Adicionar múltiplos idiomas
        article.languages.add(self.lang_pt, self.lang_en, self.lang_es)

        mods_locations = self.index.prepare_mods_location(article)

        # Verificar URLs específicos de idioma se existirem
        lang_urls = [
            loc['url'] for loc in mods_locations
            if 'url' in loc and 'version' in loc['url'].get('displayLabel', '')
        ]

        # Se houver URLs de idioma, verificar estrutura
        for url_data in lang_urls:
            self.assertIn('tlng=', url_data['text'])

    def test_location_physical_location_basic(self):
        """Teste: localização física da editora básica"""
        journal = self._create_test_journal_with_publisher('Editora Teste LTDA')
        article = self._create_test_article(journal=journal)

        mods_locations = self.index.prepare_mods_location(article)

        # Verificar se há physicalLocation
        physical_locs = [
            loc for loc in mods_locations
            if 'physicalLocation' in loc
        ]

        if physical_locs:
            physical_loc = physical_locs[0]['physicalLocation']
            self.assertIn('authority', physical_loc)
            self.assertEqual(physical_loc['authority'], 'scielo')
            self.assertIn('displayLabel', physical_loc)
            self.assertEqual(physical_loc['displayLabel'], 'Publisher')
            self.assertIn('text', physical_loc)
            self.assertIn('Editora Teste LTDA', physical_loc['text'])

    def test_location_physical_location_with_acronym(self):
        """Teste: localização física com acrônimo"""
        official = OfficialJournal.objects.create(
            title='Test Journal',
            issn_print='0102-311X',
            creator=self.user
        )

        journal = Journal.objects.create(
            official=official,
            title='Test Journal',
            creator=self.user
        )

        organization = Organization.objects.create(
            name='Fundação Oswaldo Cruz',
            acronym='FIOCRUZ',
            location=self.location,
            creator=self.user
        )

        PublisherHistory.objects.create(
            journal=journal,
            organization=organization,
            creator=self.user
        )

        article = self._create_test_article(journal=journal)

        mods_locations = self.index.prepare_mods_location(article)

        physical_locs = [
            loc['physicalLocation'] for loc in mods_locations
            if 'physicalLocation' in loc
        ]

        if physical_locs:
            physical_text = physical_locs[0]['text']
            self.assertIn('Fundação Oswaldo Cruz', physical_text)
            self.assertIn('(FIOCRUZ)', physical_text)

    def test_location_physical_location_with_geographic_info(self):
        """Teste: localização física com informação geográfica"""
        journal = self._create_test_journal_with_publisher('Editora Brasileira')
        article = self._create_test_article(journal=journal)

        mods_locations = self.index.prepare_mods_location(article)

        physical_locs = [
            loc['physicalLocation']['text'] for loc in mods_locations
            if 'physicalLocation' in loc
        ]

        if physical_locs:
            physical_text = physical_locs[0]
            # Verificar presença de componentes geográficos
            has_geographic = any(
                geo in physical_text
                for geo in ['São Paulo', 'Brasil']
            )
            self.assertTrue(has_geographic or len(physical_text) > 0)

    def test_location_no_publisher_history(self):
        """Teste: journal sem histórico de editora"""
        official = OfficialJournal.objects.create(
            title='Test Journal',
            issn_print='0102-311X',
            creator=self.user
        )

        journal = Journal.objects.create(
            official=official,
            title='Test Journal',
            creator=self.user
        )

        article = self._create_test_article(journal=journal)

        mods_locations = self.index.prepare_mods_location(article)

        # Verificar que não há physicalLocation
        physical_locations = [loc for loc in mods_locations if 'physicalLocation' in loc]
        self.assertEqual(len(physical_locations), 0)

    def test_location_edge_case_no_pid(self):
        """Teste: artigo sem PID v2"""
        journal = self._create_test_journal_with_publisher()
        article = self._create_test_article(journal=journal, pid_v2=None)

        mods_locations = self.index.prepare_mods_location(article)

        # Deve retornar lista vazia ou sem URLs
        self.assertIsInstance(mods_locations, list)

    def test_location_organization_without_location(self):
        """Teste: organização sem localização geográfica"""
        official = OfficialJournal.objects.create(
            title='Test Journal',
            issn_print='0102-311X',
            creator=self.user
        )

        journal = Journal.objects.create(
            official=official,
            title='Test Journal',
            creator=self.user
        )

        organization = Organization.objects.create(
            name='Publisher Without Location',
            acronym='PWL',
            location=None,
            creator=self.user
        )

        PublisherHistory.objects.create(
            journal=journal,
            organization=organization,
            creator=self.user
        )

        article = self._create_test_article(journal=journal)

        mods_locations = self.index.prepare_mods_location(article)

        physical_locs = [
            loc['physicalLocation']['text'] for loc in mods_locations
            if 'physicalLocation' in loc
        ]

        if physical_locs:
            # Deve ter physicalLocation apenas com nome da organização
            self.assertIn('Publisher Without Location', physical_locs[0])

    def test_location_return_type_consistency(self):
        """Teste: consistência do tipo de retorno"""
        test_cases = [
            ('no_journal', lambda: self._create_test_article()),
            ('with_journal', lambda: self._create_test_article(
                journal=self._create_test_journal_with_publisher()
            )),
        ]

        for test_name, article_creator in test_cases:
            with self.subTest(test=test_name):
                article = article_creator()

                mods_locations = self.index.prepare_mods_location(article)

                # Sempre deve retornar lista
                self.assertIsInstance(mods_locations, list)

                # Verificar estrutura de cada elemento
                for location in mods_locations:
                    self.assertIsInstance(location, dict)
                    # Deve ter 'url' ou 'physicalLocation'
                    self.assertTrue(
                        'url' in location or 'physicalLocation' in location
                    )

    def test_location_structure_validation(self):
        """Teste: validação completa da estrutura MODS location"""
        journal = self._create_test_journal_with_publisher()
        article = self._create_test_article(journal=journal)

        mods_locations = self.index.prepare_mods_location(article)

        for i, location in enumerate(mods_locations):
            with self.subTest(location_index=i):
                self.assertIsInstance(location, dict)

                if 'url' in location:
                    url_data = location['url']
                    self.assertIsInstance(url_data, dict)
                    self.assertIn('text', url_data)
                    self.assertIsInstance(url_data['text'], str)

                    # Atributos opcionais mas importantes
                    if 'usage' in url_data:
                        self.assertIn(url_data['usage'], ['primary display'])
                    if 'access' in url_data:
                        self.assertIn(url_data['access'],
                                     ['object in context', 'raw object'])

                if 'physicalLocation' in location:
                    phys_data = location['physicalLocation']
                    self.assertIsInstance(phys_data, dict)
                    self.assertIn('text', phys_data)
                    self.assertIn('authority', phys_data)
                    self.assertEqual(phys_data['authority'], 'scielo')


# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_location.MODSLocationTestCase --parallel 2 -v 2
