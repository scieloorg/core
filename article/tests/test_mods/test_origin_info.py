import uuid
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model

from article.models import Article
from article.search_indexes import ArticleOAIMODSIndex
from core.models import Language
from journal.models import Journal, OfficialJournal, PublisherHistory
from institution.models import Publisher, Institution, InstitutionIdentification
from organization.models import Organization
from location.models import Location, City, State, Country
from collection.models import Collection

User = get_user_model()


class MODSOriginInfoTestCase(TestCase):
    """
    Testes unitários otimizados para elemento originInfo MODS
    Testa estrutura e funcionalidades de informações de origem no ecossistema SciELO
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

        # Criar localizações base
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

        cls.location_main = Location.objects.create(
            country=cls.country_br,
            state=cls.state_sp,
            city=cls.city_sp,
            creator=cls.user
        )

        # Criar localizações secundárias para testes de múltiplos publishers
        cls.country_us = Country.objects.create(
            name="Estados Unidos",
            acronym="US",
            acron3="USA",
            creator=cls.user
        )

        cls.state_ny = State.objects.create(
            name="New York",
            acronym="NY",
            creator=cls.user
        )

        cls.city_ny = City.objects.create(
            name="New York",
            creator=cls.user
        )

        cls.location_secondary = Location.objects.create(
            country=cls.country_us,
            state=cls.state_ny,
            city=cls.city_ny,
            creator=cls.user
        )

        # Criar organizações base
        cls.organization_main = Organization.objects.create(
            name='Universidade de São Paulo',
            acronym='USP',
            location=cls.location_main,
            creator=cls.user
        )

        cls.organization_secondary = Organization.objects.create(
            name='Publisher Two',
            acronym='P2',
            location=cls.location_secondary,
            creator=cls.user
        )

        # Criar estrutura institucional legada para testes de fallback
        cls.inst_identification = InstitutionIdentification.objects.create(
            name='Editora Teste',
            acronym='ET',
            creator=cls.user
        )

        cls.institution = Institution.objects.create(
            institution_identification=cls.inst_identification,
            location=cls.location_main,
            creator=cls.user
        )

        cls.publisher = Publisher.objects.create(
            institution=cls.institution,
            creator=cls.user
        )

        # Criar journals base
        cls.official_journal = OfficialJournal.objects.create(
            title='Test Journal',
            creator=cls.user
        )

        cls.journal_with_contact = Journal.objects.create(
            official=cls.official_journal,
            title='Test Journal',
            contact_location=cls.location_main,
            frequency='Q',
            creator=cls.user
        )

        cls.journal_basic = Journal.objects.create(
            official=cls.official_journal,
            title='Basic Journal',
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
            'article_type': 'research-article',
            'creator': self.user
        }
        defaults.update(kwargs)
        return Article.objects.create(**defaults)

    def test_origin_info_basic_structure(self):
        """Teste: estrutura básica do originInfo"""
        article = self._create_test_article()

        origin_info = self.index.prepare_mods_origin_info(article)

        self.assertIsInstance(origin_info, list)

        if origin_info:
            self.assertIsInstance(origin_info[0], dict)
            self.assertIn("eventType", origin_info[0])
            self.assertEqual(origin_info[0]["eventType"], "publication")

    def test_origin_info_date_issued_variations(self):
        """Teste: variações de dateIssued"""
        date_test_cases = [
            # (year, month, day, expected_format)
            ('2023', '12', '15', '2023-12-15'),
            ('2023', '6', None, '2023-06'),
            ('2023', None, None, '2023'),
            ('', '', '', None),  # caso vazio
        ]

        for year, month, day, expected in date_test_cases:
            with self.subTest(date_case=f"{year}-{month}-{day}"):
                article = self._create_test_article(
                    pub_date_year=year,
                    pub_date_month=month,
                    pub_date_day=day
                )

                origin_info = self.index.prepare_mods_origin_info(article)

                if expected:
                    self.assertTrue(origin_info)
                    date_issued = origin_info[0]["dateIssued"]
                    self.assertEqual(date_issued["text"], expected)
                    self.assertEqual(date_issued["encoding"], "w3cdtf")
                    self.assertEqual(date_issued["keyDate"], "yes")
                else:
                    # Caso vazio - não deve ter dateIssued
                    if origin_info:
                        self.assertNotIn("dateIssued", origin_info[0])

    def test_origin_info_publisher_organization(self):
        """Teste: publisher via Organization (estrutura nova)"""
        article = self._create_test_article(journal=self.journal_basic)

        # Criar publisher_history com organization
        PublisherHistory.objects.create(
            journal=self.journal_basic,
            organization=self.organization_main,
            creator=self.user
        )

        origin_info = self.index.prepare_mods_origin_info(article)

        self.assertIn("publisher", origin_info[0])
        publishers = origin_info[0]["publisher"]
        self.assertIn("Universidade de São Paulo (USP)", publishers)

    def test_origin_info_publisher_institution_fallback(self):
        """Teste: publisher via Institution (fallback legado)"""
        article = self._create_test_article(journal=self.journal_basic)

        # Publisher history com institution (sem organization)
        PublisherHistory.objects.create(
            journal=self.journal_basic,
            institution=self.publisher,
            creator=self.user
        )

        origin_info = self.index.prepare_mods_origin_info(article)

        self.assertIn("publisher", origin_info[0])
        publishers = origin_info[0]["publisher"]
        self.assertIn("Editora Teste (ET)", publishers)

    def test_origin_info_multiple_publishers(self):
        """Teste: múltiplos publishers via publisher_history"""
        article = self._create_test_article(journal=self.journal_basic)

        # Múltiplos publisher histories
        PublisherHistory.objects.create(
            journal=self.journal_basic,
            organization=self.organization_main,
            creator=self.user
        )

        PublisherHistory.objects.create(
            journal=self.journal_basic,
            organization=self.organization_secondary,
            creator=self.user
        )

        origin_info = self.index.prepare_mods_origin_info(article)

        publishers = origin_info[0]["publisher"]
        self.assertEqual(len(publishers), 2)
        self.assertIn("Universidade de São Paulo (USP)", publishers)
        self.assertIn("Publisher Two (P2)", publishers)

    def test_origin_info_place_contact_location_priority(self):
        """Teste: place via contact_location do Journal (prioridade alta)"""
        article = self._create_test_article(journal=self.journal_with_contact)

        origin_info = self.index.prepare_mods_origin_info(article)

        self.assertIn("place", origin_info[0])
        places = origin_info[0]["place"]
        place_terms = places[0]["placeTerm"]

        # Verificar elementos geográficos textuais
        place_texts = [term["text"] for term in place_terms if term["type"] == "text"]
        self.assertIn("São Paulo", place_texts)  # cidade/estado
        self.assertIn("Brasil", place_texts)  # país

    def test_origin_info_place_publisher_fallback(self):
        """Teste: place via Organization do publisher (fallback)"""
        article = self._create_test_article(journal=self.journal_basic)

        PublisherHistory.objects.create(
            journal=self.journal_basic,
            organization=self.organization_main,
            creator=self.user
        )

        origin_info = self.index.prepare_mods_origin_info(article)

        self.assertIn("place", origin_info[0])
        places = origin_info[0]["place"]
        place_terms = places[0]["placeTerm"]

        place_texts = [term["text"] for term in place_terms if term["type"] == "text"]
        self.assertIn("Brasil", place_texts)

    def test_origin_info_place_codes_with_authority(self):
        """Teste: códigos de lugar com autoridade apropriada"""
        article = self._create_test_article(journal=self.journal_with_contact)

        origin_info = self.index.prepare_mods_origin_info(article)

        places = origin_info[0]["place"]
        place_terms = places[0]["placeTerm"]

        # Verificar códigos com autoridade
        code_terms = [term for term in place_terms if term["type"] == "code"]

        # Código do estado (ISO 3166-2)
        state_code = next((t for t in code_terms if t.get("authority") == "iso3166-2"), None)
        self.assertIsNotNone(state_code)
        self.assertEqual(state_code["text"], "SP")

        # Código do país (alpha-2)
        country_code_2 = next((t for t in code_terms if t.get("authority") == "iso3166-1-alpha-2"), None)
        self.assertIsNotNone(country_code_2)
        self.assertEqual(country_code_2["text"], "BR")

        # Código do país (alpha-3)
        country_code_3 = next((t for t in code_terms if t.get("authority") == "iso3166-1-alpha-3"), None)
        self.assertIsNotNone(country_code_3)
        self.assertEqual(country_code_3["text"], "BRA")

    def test_origin_info_frequency_handling(self):
        """Teste: frequency do Journal"""
        frequency_cases = [
            ('Q', 'Q'),  # Quarterly
            ('M', 'M'),  # Monthly
            ('B', 'B'),  # Bimonthly
            ('', None),  # Empty
        ]

        for input_freq, expected_freq in frequency_cases:
            with self.subTest(frequency=input_freq):
                # Criar journal com frequency específica
                journal = Journal.objects.create(
                    official=self.official_journal,
                    title=f'Journal {input_freq}',
                    frequency=input_freq,
                    creator=self.user
                )

                article = self._create_test_article(journal=journal)
                origin_info = self.index.prepare_mods_origin_info(article)

                if expected_freq:
                    self.assertIn("frequency", origin_info[0])
                    self.assertEqual(origin_info[0]["frequency"], expected_freq)
                else:
                    if origin_info:
                        self.assertNotIn("frequency", origin_info[0])

    def test_origin_info_language_attribute(self):
        """Teste: atributo lang do idioma principal"""
        language_cases = [
            (self.lang_pt, 'pt'),
            (self.lang_en, 'en'),
        ]

        for language, expected_code in language_cases:
            with self.subTest(language=expected_code):
                article = self._create_test_article()
                article.languages.add(language)

                origin_info = self.index.prepare_mods_origin_info(article)

                self.assertIn("lang", origin_info[0])
                self.assertEqual(origin_info[0]["lang"], expected_code)

    def test_origin_info_edge_cases(self):
        """Teste: casos extremos e tratamento de erros"""
        edge_cases = [
            ('no_journal', lambda: self._create_test_article(journal=None)),
            ('empty_dates', lambda: self._create_test_article(
                pub_date_year='',
                pub_date_month='   ',
                pub_date_day=None
            )),
        ]

        for case_name, article_creator in edge_cases:
            with self.subTest(case=case_name):
                article = article_creator()

                origin_info = self.index.prepare_mods_origin_info(article)

                # Deve sempre retornar lista válida
                self.assertIsInstance(origin_info, list)

                if case_name == 'no_journal':
                    # Deve ter apenas eventType
                    if origin_info:
                        self.assertEqual(origin_info[0]["eventType"], "publication")
                        self.assertNotIn("publisher", origin_info[0])
                        self.assertNotIn("place", origin_info[0])
                        self.assertNotIn("frequency", origin_info[0])

                elif case_name == 'empty_dates':
                    # Não deve ter dateIssued com strings vazias
                    if origin_info:
                        self.assertNotIn("dateIssued", origin_info[0])

    def test_origin_info_complete_scenario(self):
        """Teste: cenário completo com todos os elementos"""
        article = self._create_test_article(
            journal=self.journal_with_contact,
            pub_date_year='2023',
            pub_date_month='12',
            pub_date_day='25'
        )
        article.languages.add(self.lang_en)

        # Adicionar publisher history
        PublisherHistory.objects.create(
            journal=self.journal_with_contact,
            organization=self.organization_main,
            creator=self.user
        )

        origin_info = self.index.prepare_mods_origin_info(article)

        # Verificar estrutura completa
        origin_data = origin_info[0]

        # Campos obrigatórios
        self.assertEqual(origin_data['eventType'], 'publication')

        # Data estruturada
        date_issued = origin_data['dateIssued']
        self.assertEqual(date_issued['text'], '2023-12-25')
        self.assertEqual(date_issued['encoding'], 'w3cdtf')
        self.assertEqual(date_issued['keyDate'], 'yes')

        # Outros campos
        self.assertEqual(origin_data['frequency'], 'Q')
        self.assertEqual(origin_data['lang'], 'en')

        # Campos complexos
        self.assertIn('publisher', origin_data)
        self.assertIn('place', origin_data)
        self.assertIn('Universidade de São Paulo (USP)', origin_data['publisher'])

    def test_origin_info_return_consistency(self):
        """Teste: consistência do tipo de retorno"""
        consistency_tests = [
            ('basic_article', lambda: self._create_test_article()),
            ('article_with_journal', lambda: self._create_test_article(journal=self.journal_with_contact)),
            ('article_with_dates', lambda: self._create_test_article(
                pub_date_year='2023',
                pub_date_month='6'
            )),
        ]

        for test_name, article_creator in consistency_tests:
            with self.subTest(test=test_name):
                article = article_creator()

                origin_info = self.index.prepare_mods_origin_info(article)

                # Sempre deve retornar lista
                self.assertIsInstance(origin_info, list)

                # Se não vazio, deve ter estrutura válida
                if origin_info:
                    self.assertIsInstance(origin_info[0], dict)
                    self.assertIn("eventType", origin_info[0])

                    # Verificar estrutura de campos complexos quando presentes
                    if "dateIssued" in origin_info[0]:
                        date_issued = origin_info[0]["dateIssued"]
                        self.assertIn("text", date_issued)
                        self.assertIn("encoding", date_issued)
                        self.assertIn("keyDate", date_issued)

                    if "place" in origin_info[0]:
                        places = origin_info[0]["place"]
                        self.assertIsInstance(places, list)
                        if places:
                            self.assertIn("placeTerm", places[0])
                            self.assertIsInstance(places[0]["placeTerm"], list)

    def test_origin_info_publisher_history_priority(self):
        """Teste: prioridade entre diferentes fontes de publisher"""
        article = self._create_test_article(journal=self.journal_basic)

        # Adicionar ambos os tipos de publisher history
        PublisherHistory.objects.create(
            journal=self.journal_basic,
            organization=self.organization_main,
            creator=self.user
        )

        PublisherHistory.objects.create(
            journal=self.journal_basic,
            institution=self.publisher,
            creator=self.user
        )

        origin_info = self.index.prepare_mods_origin_info(article)

        publishers = origin_info[0]["publisher"]

        # Deve incluir ambos os publishers
        self.assertGreaterEqual(len(publishers), 2)

        # Verificar presença dos publishers específicos
        publisher_texts = [p for p in publishers if isinstance(p, str)]
        org_present = any("Universidade de São Paulo" in p for p in publisher_texts)
        inst_present = any("Editora Teste" in p for p in publisher_texts)

        self.assertTrue(org_present or inst_present)

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_origin_info.MODSOriginInfoTestCase --parallel 2 -v 2
