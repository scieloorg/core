import uuid
from django.test import TestCase
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


class MODSNameTestCase(TestCase):
    """
    Testes unitários otimizados para elemento name MODS
    Testa estrutura e funcionalidades de nomes no ecossistema SciELO
    """

    @classmethod
    def setUpTestData(cls):
        """Dados compartilhados entre testes para melhor performance"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

        # Criar localização base uma vez
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

        # Criar instituição base
        cls.institution_id = InstitutionIdentification.objects.create(
            name="Universidade de São Paulo",
            acronym="USP",
            is_official=True,
            creator=cls.user
        )

        cls.institution = Institution.objects.create(
            institution_identification=cls.institution_id,
            location=cls.location,
            level_1="Instituto de Matemática e Estatística",
            level_2="Departamento de Ciência da Computação",
            creator=cls.user
        )

        cls.affiliation = Affiliation.objects.create(
            institution=cls.institution,
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

    def _create_test_person_name(self, given_names='João', last_name='Silva', suffix=None, declared_name=None):
        """Helper para criar PersonName estruturado"""
        if declared_name:
            return PersonName.objects.create(
                declared_name=declared_name,
                creator=self.user
            )

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

    def _create_test_researcher(self, person_name=None, affiliation=None):
        """Helper para criar Researcher de teste"""
        return Researcher.objects.create(
            person_name=person_name,
            affiliation=affiliation,
            creator=self.user
        )

    def _add_identifier_to_researcher(self, researcher, identifier_value, source_name):
        """Helper para adicionar identificadores via ResearcherAKA"""
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

    def test_name_no_names(self):
        """Teste: artigo sem nomes"""
        article = self._create_test_article()

        mods_names = self.index.prepare_mods_name(article)

        self.assertEqual(len(mods_names), 0)

    def test_name_single_personal_basic(self):
        """Teste: nome pessoal básico sem identificadores"""
        article = self._create_test_article()
        person_name = self._create_test_person_name('Maria', 'Santos')
        researcher = self._create_test_researcher(person_name=person_name)
        article.researchers.add(researcher)

        mods_names = self.index.prepare_mods_name(article)

        self.assertEqual(len(mods_names), 1)
        mods_name = mods_names[0]

        # Verificar estrutura básica
        self.assertEqual(mods_name['type'], 'personal')

        # Verificar role estruturado
        self.assertIn('role', mods_name)
        role_term = mods_name['role']['roleTerm']
        self.assertEqual(role_term['type'], 'text')
        self.assertEqual(role_term['authority'], 'marcrelator')
        self.assertEqual(role_term['text'], 'author')

        # Verificar namePart estruturado
        name_parts = mods_name['namePart']
        self.assertIsInstance(name_parts, list)

        given_part = next((p for p in name_parts if p.get('type') == 'given'), None)
        family_part = next((p for p in name_parts if p.get('type') == 'family'), None)

        self.assertIsNotNone(given_part)
        self.assertEqual(given_part['text'], 'Maria')
        self.assertIsNotNone(family_part)
        self.assertEqual(family_part['text'], 'Santos')

    def test_name_personal_with_suffix(self):
        """Teste: nome pessoal com sufixo"""
        article = self._create_test_article()
        person_name = self._create_test_person_name('Carlos', 'Silva', 'Jr.')
        researcher = self._create_test_researcher(person_name=person_name)
        article.researchers.add(researcher)

        mods_names = self.index.prepare_mods_name(article)
        name_parts = mods_names[0]['namePart']

        given_part = next((p for p in name_parts if p.get('type') == 'given'), None)
        family_part = next((p for p in name_parts if p.get('type') == 'family'), None)
        terms_part = next((p for p in name_parts if p.get('type') == 'termsOfAddress'), None)

        self.assertEqual(given_part['text'], 'Carlos')
        self.assertEqual(family_part['text'], 'Silva')
        self.assertEqual(terms_part['text'], 'Jr.')

    def test_name_personal_with_identifiers(self):
        """Teste: nome pessoal com diferentes identificadores"""
        identifier_cases = [
            ('0000-0001-2345-6789', 'ORCID', 'orcid'),
            ('1234567890123456', 'LATTES', 'lattes'),
            ('12345678', 'SCOPUS', 'scopus'),
        ]

        for identifier_value, source_name, expected_type in identifier_cases:
            with self.subTest(identifier_type=expected_type):
                article = self._create_test_article()
                person_name = self._create_test_person_name('Ana', 'Costa')
                researcher = self._create_test_researcher(person_name=person_name)

                self._add_identifier_to_researcher(researcher, identifier_value, source_name)
                article.researchers.add(researcher)

                mods_names = self.index.prepare_mods_name(article)
                mods_name = mods_names[0]

                # Verificar nameIdentifier
                self.assertIn('nameIdentifier', mods_name)
                identifiers = mods_name['nameIdentifier']
                self.assertEqual(len(identifiers), 1)

                identifier = identifiers[0]
                self.assertEqual(identifier['type'], expected_type)
                self.assertEqual(identifier['text'], identifier_value)

    def test_name_personal_with_affiliation(self):
        """Teste: nome pessoal com afiliação estruturada"""
        article = self._create_test_article()
        person_name = self._create_test_person_name('Roberto', 'Oliveira')
        researcher = self._create_test_researcher(
            person_name=person_name,
            affiliation=self.affiliation
        )
        article.researchers.add(researcher)

        mods_names = self.index.prepare_mods_name(article)
        mods_name = mods_names[0]

        # Verificar afiliação
        self.assertIn('affiliation', mods_name)
        affiliation_text = mods_name['affiliation']

        # Verificar elementos da estrutura hierárquica
        self.assertIn('Universidade de São Paulo', affiliation_text)
        self.assertIn('Instituto de Matemática e Estatística', affiliation_text)
        self.assertIn('São Paulo', affiliation_text)

    def test_name_multiple_identifiers_same_researcher(self):
        """Teste: múltiplos identificadores para o mesmo pesquisador"""
        article = self._create_test_article()
        person_name = self._create_test_person_name('Pedro', 'Santos')
        researcher = self._create_test_researcher(person_name=person_name)

        # Adicionar múltiplos identificadores
        identifiers_data = [
            ('0000-0002-1234-5678', 'ORCID'),
            ('1234567890123456', 'LATTES'),
            ('98765432', 'SCOPUS'),
        ]

        for identifier_value, source_name in identifiers_data:
            self._add_identifier_to_researcher(researcher, identifier_value, source_name)

        article.researchers.add(researcher)

        mods_names = self.index.prepare_mods_name(article)
        mods_name = mods_names[0]
        identifiers = mods_name['nameIdentifier']

        self.assertEqual(len(identifiers), 3)

        # Verificar cada identificador
        orcid_id = next((i for i in identifiers if i['type'] == 'orcid'), None)
        lattes_id = next((i for i in identifiers if i['type'] == 'lattes'), None)
        scopus_id = next((i for i in identifiers if i['type'] == 'scopus'), None)

        self.assertIsNotNone(orcid_id)
        self.assertEqual(orcid_id['text'], '0000-0002-1234-5678')

        self.assertIsNotNone(lattes_id)
        self.assertEqual(lattes_id['text'], '1234567890123456')

        self.assertIsNotNone(scopus_id)
        self.assertEqual(scopus_id['text'], '98765432')

    def test_name_multiple_researchers(self):
        """Teste: múltiplos pesquisadores"""
        article = self._create_test_article()

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

        for expected_name in researchers_data:
            self.assertIn(expected_name, name_texts)

    def test_name_corporate_basic(self):
        """Teste: nomes corporativos básicos"""
        article = self._create_test_article()

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

    def test_name_corporate_with_affiliation(self):
        """Teste: corporativo com afiliação"""
        article = self._create_test_article()

        institutional_author = InstitutionalAuthor.objects.create(
            collab="Laboratório Nacional de Computação Científica",
            affiliation=self.affiliation,
            creator=self.user
        )
        article.collab.add(institutional_author)

        mods_names = self.index.prepare_mods_name(article)
        mods_name = mods_names[0]

        self.assertEqual(mods_name['type'], 'corporate')
        self.assertIn('affiliation', mods_name)

        affiliation_text = mods_name['affiliation']
        self.assertIn('Universidade de São Paulo', affiliation_text)

    def test_name_mixed_scenario_complete(self):
        """Teste: cenário completo com pessoais e corporativos"""
        article = self._create_test_article()

        # Pesquisador com identificador e afiliação
        person_name1 = self._create_test_person_name('Ana', 'Silva')
        researcher1 = self._create_test_researcher(
            person_name=person_name1,
            affiliation=self.affiliation
        )
        self._add_identifier_to_researcher(researcher1, '0000-0001-1111-1111', 'ORCID')
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

        # Verificar pesquisador com identificadores
        with_identifiers = [n for n in personal_names if 'nameIdentifier' in n]
        self.assertEqual(len(with_identifiers), 1)

        # Verificar corporativo
        corporate = corporate_names[0]
        self.assertEqual(corporate['namePart'], 'Instituto Nacional de Pesquisa')
        self.assertIn('affiliation', corporate)

    def test_name_edge_cases_handling(self):
        """Teste: casos extremos e tratamento de erros"""
        edge_cases = [
            # (description, setup_function)
            ('researcher_without_person_name', lambda article: (
                article.researchers.add(self._create_test_researcher(person_name=None))
            )),
            ('person_name_only_declared', lambda article: (
                article.researchers.add(self._create_test_researcher(
                    person_name=self._create_test_person_name(declared_name="Dr. Maria da Silva Santos")
                ))
            )),
            ('empty_institutional_collab', lambda article: (
                article.collab.add(InstitutionalAuthor.objects.create(
                    collab="",
                    creator=self.user
                ))
            )),
        ]

        for case_desc, setup_func in edge_cases:
            with self.subTest(case=case_desc):
                article = self._create_test_article()
                setup_func(article)

                mods_names = self.index.prepare_mods_name(article)

                # Deve sempre retornar lista válida
                self.assertIsInstance(mods_names, list)

                if case_desc == 'researcher_without_person_name':
                    # Deve ser ignorado
                    self.assertEqual(len(mods_names), 0)
                elif case_desc == 'person_name_only_declared':
                    # Deve usar fallback
                    self.assertEqual(len(mods_names), 1)
                    name_parts = mods_names[0]['namePart']
                    self.assertEqual(name_parts[0]['text'], "Dr. Maria da Silva Santos")

    def test_name_structure_consistency_validation(self):
        """Teste: validação de consistência da estrutura"""
        article = self._create_test_article()
        person_name = self._create_test_person_name('Test', 'User')
        researcher = self._create_test_researcher(person_name=person_name)
        article.researchers.add(researcher)

        mods_names = self.index.prepare_mods_name(article)

        # Validar estrutura MODS completa
        for mods_name in mods_names:
            self.assertIsInstance(mods_name, dict)
            self.assertIn('type', mods_name)
            self.assertIn(mods_name['type'], ['personal', 'corporate'])

            # Verificar role sempre presente
            self.assertIn('role', mods_name)
            role = mods_name['role']
            self.assertIn('roleTerm', role)
            self.assertIn('type', role['roleTerm'])
            self.assertIn('authority', role['roleTerm'])
            self.assertIn('text', role['roleTerm'])

            # Verificar namePart
            if mods_name['type'] == 'personal':
                self.assertIn('namePart', mods_name)
                self.assertIsInstance(mods_name['namePart'], list)
            else:  # corporate
                self.assertIn('namePart', mods_name)
                self.assertIsInstance(mods_name['namePart'], str)

    def test_name_identifier_authority_mapping(self):
        """Teste: mapeamento correto de authorities para identificadores"""
        identifier_mappings = [
            ('ORCID', 'orcid', 'orcid'),
            ('LATTES', 'lattes', 'lattes'),
            ('SCOPUS', 'scopus', 'scopus'),
            ('RESEARCHERID', 'researcherid', 'researcherid'),
        ]

        for source_name, expected_type, expected_authority in identifier_mappings:
            with self.subTest(source=source_name):
                article = self._create_test_article()
                person_name = self._create_test_person_name('Test', 'User')
                researcher = self._create_test_researcher(person_name=person_name)

                self._add_identifier_to_researcher(researcher, '12345', source_name)
                article.researchers.add(researcher)

                mods_names = self.index.prepare_mods_name(article)
                identifiers = mods_names[0]['nameIdentifier']

                identifier = identifiers[0]
                self.assertEqual(identifier['type'], expected_type)
                if 'authority' in identifier:
                    self.assertEqual(identifier['authority'], expected_authority)

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_name.MODSNameTestCase --parallel 2 -v 2
