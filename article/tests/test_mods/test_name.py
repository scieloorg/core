import uuid
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from article.models import Article
from researcher.models import (
    Researcher, PersonName, Affiliation,
    ResearcherIdentifier, ResearcherAKA, InstitutionalAuthor
)
from institution.models import Institution, InstitutionIdentification
from location.models import Location, City, State, Country
from article.search_indexes import ArticleOAIMODSIndex

User = get_user_model()


class MODSNameTestCase(TransactionTestCase):
    """
    Testes unitários focados no índice MODS para elemento name
    Corrigidos para trabalhar com implementação enriquecida
    """

    def setUp(self):
        """Configuração inicial dos testes com dados mínimos necessários"""
        self.user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4().hex[:8]}',
            email=f'test_{uuid.uuid4().hex[:8]}@example.com',
            password='testpass'
        )

        # Criar localização mínima para testes
        self.country_br = Country.objects.create(
            name="Brasil",
            acronym="BR",
            acron3="BRA",
            creator=self.user
        )

        self.state_sp = State.objects.create(
            name="São Paulo",
            acronym="SP",
            creator=self.user
        )

        self.city_sp = City.objects.create(
            name="São Paulo",
            creator=self.user
        )

        self.location = Location.objects.create(
            country=self.country_br,
            state=self.state_sp,
            city=self.city_sp,
            creator=self.user
        )

        # Criar instituição mínima
        self.institution_id = InstitutionIdentification.objects.create(
            name="Universidade de São Paulo",
            acronym="USP",
            is_official=True,
            creator=self.user
        )

        self.institution = Institution.objects.create(
            institution_identification=self.institution_id,
            location=self.location,
            level_1="Instituto de Matemática e Estatística",
            level_2="Departamento de Ciência da Computação",
            creator=self.user
        )

        self.affiliation = Affiliation.objects.create(
            institution=self.institution,
            creator=self.user
        )

        self.index = ArticleOAIMODSIndex()

    def tearDown(self):
        """Limpeza após cada teste"""
        ResearcherAKA.objects.all().delete()
        ResearcherIdentifier.objects.all().delete()
        Researcher.objects.all().delete()
        PersonName.objects.all().delete()
        InstitutionalAuthor.objects.all().delete()
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

    def _create_test_person_name(self, given_names='João', last_name='Silva', suffix=None):
        """Helper para criar PersonName estruturado"""
        fullname = f"{given_names} {last_name}"
        if suffix:
            fullname += f" {suffix}"

        return PersonName.objects.create(
            given_names=given_names,
            last_name=last_name,
            suffix=suffix,
            fullname=fullname,
            creator=self.user
        )

    def _create_test_researcher(self, person_name, affiliation=None):
        """Helper para criar Researcher de teste"""
        return Researcher.objects.create(
            person_name=person_name,
            affiliation=affiliation,
            creator=self.user
        )

    def _add_orcid_to_researcher(self, researcher, orcid):
        """Helper para adicionar ORCID via ResearcherAKA"""
        identifier = ResearcherIdentifier.objects.create(
            identifier=orcid,
            source_name='ORCID',
            creator=self.user
        )
        ResearcherAKA.objects.create(
            researcher=researcher,
            researcher_identifier=identifier,
            creator=self.user
        )

    def _add_identifier_to_researcher(self, researcher, identifier_value, source_name):
        """Helper genérico para adicionar identificadores"""
        identifier = ResearcherIdentifier.objects.create(
            identifier=identifier_value,
            source_name=source_name,
            creator=self.user
        )
        ResearcherAKA.objects.create(
            researcher=researcher,
            researcher_identifier=identifier,
            creator=self.user
        )

    def test_researcher_creation_basic(self):
        """Teste básico de criação do modelo Researcher"""
        article = self._create_test_article()
        person_name = self._create_test_person_name()
        researcher = self._create_test_researcher(
            person_name=person_name,
            affiliation=self.affiliation
        )
        article.researchers.add(researcher)

        # Validações básicas do modelo
        self.assertIsNotNone(researcher.id)
        self.assertEqual(researcher.person_name, person_name)
        self.assertEqual(researcher.affiliation, self.affiliation)
        self.assertEqual(article.researchers.count(), 1)

    def test_mods_index_no_names(self):
        """Teste índice MODS: artigo sem nomes"""
        article = self._create_test_article()

        mods_names = self.index.prepare_mods_name(article)
        self.assertEqual(len(mods_names), 0)

    def test_mods_index_single_personal_name_basic(self):
        """Teste índice MODS: nome pessoal básico sem identificadores"""
        article = self._create_test_article()
        person_name = self._create_test_person_name('Maria', 'Santos')
        researcher = self._create_test_researcher(person_name=person_name)
        article.researchers.add(researcher)

        # Testar estrutura MODS enriquecida
        mods_names = self.index.prepare_mods_name(article)
        self.assertEqual(len(mods_names), 1)

        mods_name = mods_names[0]

        # Verificar estrutura básica
        self.assertEqual(mods_name['type'], 'personal')

        # Verificar role estruturado conforme MODS
        self.assertIn('role', mods_name)
        self.assertIn('roleTerm', mods_name['role'])
        self.assertEqual(mods_name['role']['roleTerm']['type'], 'text')
        self.assertEqual(mods_name['role']['roleTerm']['authority'], 'marcrelator')
        self.assertEqual(mods_name['role']['roleTerm']['text'], 'author')

        # Verificar namePart estruturado
        self.assertIn('namePart', mods_name)
        name_parts = mods_name['namePart']
        self.assertIsInstance(name_parts, list)

        # Encontrar partes específicas
        given_part = next((p for p in name_parts if p.get('type') == 'given'), None)
        family_part = next((p for p in name_parts if p.get('type') == 'family'), None)

        self.assertIsNotNone(given_part)
        self.assertEqual(given_part['text'], 'Maria')
        self.assertIsNotNone(family_part)
        self.assertEqual(family_part['text'], 'Santos')

        # Não deve ter identificadores sem dados
        self.assertNotIn('nameIdentifier', mods_name)

    def test_mods_index_personal_name_with_suffix(self):
        """Teste índice MODS: nome com sufixo (Jr., Sr., etc.)"""
        article = self._create_test_article()
        person_name = self._create_test_person_name('Carlos', 'Silva', 'Jr.')
        researcher = self._create_test_researcher(person_name=person_name)
        article.researchers.add(researcher)

        mods_names = self.index.prepare_mods_name(article)
        self.assertEqual(len(mods_names), 1)

        mods_name = mods_names[0]
        name_parts = mods_name['namePart']

        # Verificar todas as partes do nome
        given_part = next((p for p in name_parts if p.get('type') == 'given'), None)
        family_part = next((p for p in name_parts if p.get('type') == 'family'), None)
        terms_part = next((p for p in name_parts if p.get('type') == 'termsOfAddress'), None)

        self.assertEqual(given_part['text'], 'Carlos')
        self.assertEqual(family_part['text'], 'Silva')
        self.assertEqual(terms_part['text'], 'Jr.')

    def test_mods_index_personal_name_with_orcid(self):
        """Teste índice MODS: nome pessoal com ORCID"""
        article = self._create_test_article()
        person_name = self._create_test_person_name('Ana', 'Costa')
        researcher = self._create_test_researcher(person_name=person_name)

        # Adicionar ORCID via sistema ResearcherAKA
        self._add_orcid_to_researcher(researcher, '0000-0001-2345-6789')
        article.researchers.add(researcher)

        mods_names = self.index.prepare_mods_name(article)
        self.assertEqual(len(mods_names), 1)

        mods_name = mods_names[0]

        # Verificar nameIdentifier estruturado
        self.assertIn('nameIdentifier', mods_name)
        identifiers = mods_name['nameIdentifier']
        self.assertIsInstance(identifiers, list)
        self.assertEqual(len(identifiers), 1)

        orcid_identifier = identifiers[0]
        self.assertEqual(orcid_identifier['type'], 'orcid')
        self.assertEqual(orcid_identifier['text'], '0000-0001-2345-6789')
        self.assertEqual(orcid_identifier['authority'], 'orcid')

    def test_mods_index_personal_name_with_affiliation(self):
        """Teste índice MODS: nome pessoal com afiliação estruturada"""
        article = self._create_test_article()
        person_name = self._create_test_person_name('Roberto', 'Oliveira')
        researcher = self._create_test_researcher(
            person_name=person_name,
            affiliation=self.affiliation
        )
        article.researchers.add(researcher)

        mods_names = self.index.prepare_mods_name(article)
        self.assertEqual(len(mods_names), 1)

        mods_name = mods_names[0]

        # Verificar afiliação estruturada
        self.assertIn('affiliation', mods_name)
        affiliation_text = mods_name['affiliation']

        # Verificar que contém elementos da estrutura hierárquica
        self.assertIn('Universidade de São Paulo', affiliation_text)
        self.assertIn('Instituto de Matemática e Estatística', affiliation_text)
        self.assertIn('São Paulo', affiliation_text)

    def test_mods_index_multiple_identifiers(self):
        """Teste índice MODS: múltiplos identificadores (ORCID + LATTES)"""
        article = self._create_test_article()
        person_name = self._create_test_person_name('Pedro', 'Santos')
        researcher = self._create_test_researcher(person_name=person_name)

        # Adicionar múltiplos identificadores
        self._add_orcid_to_researcher(researcher, '0000-0002-1234-5678')
        self._add_identifier_to_researcher(researcher, '1234567890123456', 'LATTES')
        article.researchers.add(researcher)

        mods_names = self.index.prepare_mods_name(article)
        self.assertEqual(len(mods_names), 1)

        mods_name = mods_names[0]
        identifiers = mods_name['nameIdentifier']
        self.assertEqual(len(identifiers), 2)

        # Verificar identificadores específicos
        orcid_id = next((i for i in identifiers if i['type'] == 'orcid'), None)
        lattes_id = next((i for i in identifiers if i['type'] == 'lattes'), None)

        self.assertIsNotNone(orcid_id)
        self.assertEqual(orcid_id['text'], '0000-0002-1234-5678')

        self.assertIsNotNone(lattes_id)
        self.assertEqual(lattes_id['text'], '1234567890123456')

    def test_mods_index_multiple_personal_names(self):
        """Teste índice MODS: múltiplos pesquisadores"""
        article = self._create_test_article()

        # Criar múltiplos pesquisadores
        researchers_data = [
            ('João', 'Silva'),
            ('Maria', 'Costa'),
            ('Pedro', 'Santos')
        ]

        for given, family in researchers_data:
            person_name = self._create_test_person_name(given, family)
            researcher = self._create_test_researcher(person_name=person_name)
            article.researchers.add(researcher)

        mods_names = self.index.prepare_mods_name(article)
        self.assertEqual(len(mods_names), 3)

        # Verificar que todos são pessoais
        for mods_name in mods_names:
            self.assertEqual(mods_name['type'], 'personal')
            self.assertIn('role', mods_name)

        # Verificar nomes específicos
        name_texts = []
        for mods_name in mods_names:
            name_parts = mods_name['namePart']
            given = next(p['text'] for p in name_parts if p.get('type') == 'given')
            family = next(p['text'] for p in name_parts if p.get('type') == 'family')
            name_texts.append((given, family))

        self.assertIn(('João', 'Silva'), name_texts)
        self.assertIn(('Maria', 'Costa'), name_texts)
        self.assertIn(('Pedro', 'Santos'), name_texts)

    def test_mods_index_corporate_names_basic(self):
        """Teste índice MODS: nomes corporativos básicos"""
        article = self._create_test_article()

        # Criar colaboração institucional
        institutional_author = InstitutionalAuthor.objects.create(
            collab="Consórcio Brasileiro de Pesquisa",
            creator=self.user
        )
        article.collab.add(institutional_author)

        mods_names = self.index.prepare_mods_name(article)
        self.assertEqual(len(mods_names), 1)

        mods_name = mods_names[0]
        self.assertEqual(mods_name['type'], 'corporate')
        self.assertEqual(mods_name['namePart'], 'Consórcio Brasileiro de Pesquisa')

        # Verificar role corporativo
        self.assertIn('role', mods_name)
        self.assertEqual(mods_name['role']['roleTerm']['text'], 'author')

    def test_mods_index_corporate_with_affiliation(self):
        """Teste índice MODS: corporativo com afiliação"""
        article = self._create_test_article()

        institutional_author = InstitutionalAuthor.objects.create(
            collab="Laboratório Nacional de Computação Científica",
            affiliation=self.affiliation,
            creator=self.user
        )
        article.collab.add(institutional_author)

        mods_names = self.index.prepare_mods_name(article)
        self.assertEqual(len(mods_names), 1)

        mods_name = mods_names[0]
        self.assertEqual(mods_name['type'], 'corporate')

        # Verificar afiliação corporativa
        self.assertIn('affiliation', mods_name)
        affiliation_text = mods_name['affiliation']
        self.assertIn('Universidade de São Paulo', affiliation_text)

    def test_mods_index_mixed_scenario_complete(self):
        """Teste índice MODS: cenário completo com pessoais e corporativos"""
        article = self._create_test_article()

        # Pesquisador com ORCID e afiliação
        person_name1 = self._create_test_person_name('Ana', 'Silva')
        researcher1 = self._create_test_researcher(
            person_name=person_name1,
            affiliation=self.affiliation
        )
        self._add_orcid_to_researcher(researcher1, '0000-0001-1111-1111')
        article.researchers.add(researcher1)

        # Pesquisador básico
        person_name2 = self._create_test_person_name('João', 'Costa')
        researcher2 = self._create_test_researcher(person_name=person_name2)
        article.researchers.add(researcher2)

        # Colaboração institucional
        institutional_author = InstitutionalAuthor.objects.create(
            collab="Instituto Nacional de Pesquisa",
            affiliation=self.affiliation,
            creator=self.user
        )
        article.collab.add(institutional_author)

        mods_names = self.index.prepare_mods_name(article)
        self.assertEqual(len(mods_names), 3)

        # Classificar por tipo
        personal_names = [n for n in mods_names if n['type'] == 'personal']
        corporate_names = [n for n in mods_names if n['type'] == 'corporate']

        self.assertEqual(len(personal_names), 2)
        self.assertEqual(len(corporate_names), 1)

        # Verificar pesquisador com identificador
        with_identifiers = [n for n in personal_names if 'nameIdentifier' in n]
        self.assertEqual(len(with_identifiers), 1)

        # Verificar corporativo
        corporate = corporate_names[0]
        self.assertEqual(corporate['namePart'], 'Instituto Nacional de Pesquisa')
        self.assertIn('affiliation', corporate)

    def test_mods_index_researcher_without_person_name(self):
        """Teste índice MODS: researcher sem person_name é ignorado"""
        article = self._create_test_article()

        # Criar researcher inválido
        researcher = Researcher.objects.create(
            person_name=None,
            creator=self.user
        )
        article.researchers.add(researcher)

        mods_names = self.index.prepare_mods_name(article)
        self.assertEqual(len(mods_names), 0)

    def test_mods_index_fallback_scenarios(self):
        """Teste índice MODS: cenários de fallback para dados incompletos"""
        article = self._create_test_article()

        # PersonName apenas com declared_name (sem estrutura)
        person_name = PersonName.objects.create(
            declared_name="Dr. Maria da Silva Santos",
            creator=self.user
        )
        researcher = self._create_test_researcher(person_name=person_name)
        article.researchers.add(researcher)

        mods_names = self.index.prepare_mods_name(article)
        self.assertEqual(len(mods_names), 1)

        mods_name = mods_names[0]
        name_parts = mods_name['namePart']

        # Deve usar fallback para declared_name
        self.assertEqual(len(name_parts), 1)
        self.assertEqual(name_parts[0]['text'], "Dr. Maria da Silva Santos")

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_name.MODSNameTestCase -v 2
