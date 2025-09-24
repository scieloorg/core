import uuid
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from article.models import Article
from article.search_indexes import ArticleOAIMODSIndex
from collection.models import Collection
from core.models import Language
from issue.models import Issue, TocSection
from journal.models import Journal, OfficialJournal, Subject, SubjectDescriptor, WebOfKnowledgeSubjectCategory, \
    ThematicAreaJournal
from location.models import Location, City, State, Country
from thematic_areas.models import ThematicArea
from vocabulary.models import Vocabulary, Keyword

User = get_user_model()


class MODSSubjectTestCase(TransactionTestCase):
    """
    Testes unitários focados no índice MODS para elemento subject
    Testa todos os tipos de assuntos do ecossistema SciELO
    """

    def setUp(self):
        """Configuração inicial dos testes com dados mínimos necessários"""
        self.user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4().hex[:8]}',
            email=f'test_{uuid.uuid4().hex[:8]}@example.com',
            password='testpass'
        )

        # Criar idiomas
        self.language_pt = Language.objects.create(
            name="Portuguese",
            code2="pt",
            creator=self.user
        )

        self.language_en = Language.objects.create(
            name="English",
            code2="en",
            creator=self.user
        )

        # Criar vocabulário
        self.vocabulary_decs = Vocabulary.objects.create(
            name="Health Science Descriptors",
            acronym="decs",
            creator=self.user
        )

        self.vocabulary_mesh = Vocabulary.objects.create(
            name="Medical Subject Headings",
            acronym="mesh",
            creator=self.user
        )

        # Criar localização mínima
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

        # Criar coleção
        self.collection = Collection.objects.create(
            acron3="scl",
            acron2="br",
            code="001",
            domain="www.scielo.br",
            main_name="SciELO Brasil",
            collection_type="journals",
            is_active=True,
            creator=self.user
        )

        # Criar journal oficial
        self.official_journal = OfficialJournal.objects.create(
            title="Revista Brasileira de Medicina",
            issn_print="0100-1234",
            issn_electronic="1678-5678",
            issnl="0100-1234",
            creator=self.user
        )

        # Criar journal
        self.journal = Journal.objects.create(
            official=self.official_journal,
            title="Revista Brasileira de Medicina",
            creator=self.user
        )

        # Criar issue
        self.issue = Issue.objects.create(
            journal=self.journal,
            volume="10",
            number="2",
            year="2024",
            creator=self.user
        )

        self.index = ArticleOAIMODSIndex()

    def tearDown(self):
        """Limpeza após cada teste"""
        Keyword.objects.all().delete()
        Article.objects.all().delete()
        super().tearDown()

    def _create_test_article(self, **kwargs):
        """Helper para criar artigo de teste único"""
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

    def _create_test_keyword(self, text, vocabulary=None, language=None):
        """Helper para criar keyword de teste"""
        return Keyword.objects.create(
            text=text,
            vocabulary=vocabulary or self.vocabulary_decs,
            language=language or self.language_pt,
            creator=self.user
        )

    def _create_test_toc_section(self, text, language=None):
        """Helper para criar TOC section de teste"""
        return TocSection.objects.create(
            plain_text=text,
            language=language or self.language_pt,
            creator=self.user
        )

    def test_subject_creation_basic(self):
        """Teste básico de criação do modelo com subjects"""
        article = self._create_test_article()
        keyword = self._create_test_keyword("Machine Learning")
        article.keywords.add(keyword)

        # Validações básicas
        self.assertIsNotNone(article.id)
        self.assertEqual(article.keywords.count(), 1)
        self.assertEqual(keyword.text, "Machine Learning")

    def test_mods_index_no_subjects(self):
        """Teste índice MODS: artigo sem subjects"""
        article = self._create_test_article()

        mods_subjects = self.index.prepare_mods_subject(article)
        self.assertEqual(len(mods_subjects), 0)

    def test_mods_index_single_keyword_basic(self):
        """Teste índice MODS: keyword básico sem vocabulário"""
        article = self._create_test_article()

        # Criar keyword explicitamente sem vocabulário
        keyword = Keyword.objects.create(
            text="Diabetes",
            vocabulary=None,  # Explicitamente None
            language=self.language_pt,
            creator=self.user
        )
        article.keywords.add(keyword)

        mods_subjects = self.index.prepare_mods_subject(article)
        self.assertEqual(len(mods_subjects), 1)

        subject = mods_subjects[0]
        self.assertEqual(subject['topic'], 'Diabetes')  # Estrutura simples
        self.assertEqual(subject['lang'], 'por')

    def test_mods_index_keyword_with_vocabulary_authority(self):
        """Teste índice MODS: keyword com vocabulário controlado"""
        article = self._create_test_article()

        # Usar o helper que já adiciona vocabulário por padrão
        keyword = self._create_test_keyword("Hypertension", vocabulary=self.vocabulary_mesh)
        article.keywords.add(keyword)

        mods_subjects = self.index.prepare_mods_subject(article)
        self.assertEqual(len(mods_subjects), 1)

        subject = mods_subjects[0]
        self.assertIn('topic', subject)

        # Verificar estrutura com autoridade
        topic = subject['topic']
        self.assertEqual(topic['text'], 'Hypertension')
        self.assertEqual(topic['authority'], 'mesh')

    def test_mods_index_multiple_keywords(self):
        """Teste índice MODS: múltiplas keywords"""
        article = self._create_test_article()

        # Keywords com diferentes vocabulários e idiomas
        keyword1 = self._create_test_keyword("Diabetes", self.vocabulary_decs, self.language_pt)
        keyword2 = self._create_test_keyword("Machine Learning", self.vocabulary_mesh, self.language_en)
        keyword3 = self._create_test_keyword("Inteligência Artificial", language=self.language_pt)

        article.keywords.add(keyword1, keyword2, keyword3)

        mods_subjects = self.index.prepare_mods_subject(article)
        self.assertEqual(len(mods_subjects), 3)

        # Verificar diferentes estruturas
        subjects_by_text = {s['topic'] if isinstance(s['topic'], str) else s['topic']['text']: s for s in mods_subjects}

        # Keyword com vocabulário em português
        diabetes_subject = subjects_by_text['Diabetes']
        self.assertEqual(diabetes_subject['topic']['authority'], 'decs')
        self.assertEqual(diabetes_subject['lang'], 'por')

        # Keyword com vocabulário em inglês
        ml_subject = subjects_by_text['Machine Learning']
        self.assertEqual(ml_subject['topic']['authority'], 'mesh')
        self.assertEqual(ml_subject['lang'], 'eng')

        # Keyword sem vocabulário específico
        ai_subject = subjects_by_text['Inteligência Artificial']
        self.assertEqual(ai_subject['lang'], 'por')

    def test_mods_index_journal_subject_areas(self):
        """Teste índice MODS: áreas de assunto do journal"""
        article = self._create_test_article()

        # Criar Subject areas
        subject_area1 = Subject.objects.create(
            code="medicina",
            value="Medicina",
            creator=self.user
        )
        subject_area2 = Subject.objects.create(
            code="ciencias-saude",
            value="Ciências da Saúde",
            creator=self.user
        )

        # Adicionar ao journal
        article.journal.subject.add(subject_area1, subject_area2)

        mods_subjects = self.index.prepare_mods_subject(article)
        self.assertEqual(len(mods_subjects), 2)

        # Verificar estrutura de subject areas
        subject_texts = [s['topic']['text'] for s in mods_subjects]
        self.assertIn('Medicina', subject_texts)
        self.assertIn('Ciências da Saúde', subject_texts)

        # Verificar autoridade
        for subject in mods_subjects:
            self.assertEqual(subject['topic']['authority'], 'scielo-subject-area')

    def test_mods_index_journal_subject_descriptors(self):
        """Teste índice MODS: descritores de assunto do journal"""
        article = self._create_test_article()

        # Criar Subject descriptors
        descriptor1 = SubjectDescriptor.objects.create(
            value="Endocrinologia",
            creator=self.user
        )
        descriptor2 = SubjectDescriptor.objects.create(
            value="Metabolismo",
            creator=self.user
        )

        article.journal.subject_descriptor.add(descriptor1, descriptor2)

        mods_subjects = self.index.prepare_mods_subject(article)
        self.assertEqual(len(mods_subjects), 2)

        # Verificar descritores
        descriptor_texts = [s['topic']['text'] for s in mods_subjects]
        self.assertIn('Endocrinologia', descriptor_texts)
        self.assertIn('Metabolismo', descriptor_texts)

        # Verificar autoridade específica
        for subject in mods_subjects:
            self.assertEqual(subject['topic']['authority'], 'scielo-descriptor')

    def test_mods_index_wos_subject_categories(self):
        """Teste índice MODS: categorias WoS do journal"""
        article = self._create_test_article()

        # Criar WoS categories
        wos_category1 = WebOfKnowledgeSubjectCategory.objects.create(
            value="Medicine, General & Internal",
            creator=self.user
        )
        wos_category2 = WebOfKnowledgeSubjectCategory.objects.create(
            value="Endocrinology & Metabolism",
            creator=self.user
        )

        article.journal.wos_area.add(wos_category1, wos_category2)

        mods_subjects = self.index.prepare_mods_subject(article)
        self.assertEqual(len(mods_subjects), 2)

        # Verificar categorias WoS
        wos_texts = [s['topic']['text'] for s in mods_subjects]
        self.assertIn('Medicine, General & Internal', wos_texts)
        self.assertIn('Endocrinology & Metabolism', wos_texts)

        # Verificar autoridade e URI WoS
        for subject in mods_subjects:
            self.assertEqual(subject['topic']['authority'], 'wos')
            self.assertEqual(subject['topic']['authorityURI'], 'http://apps.webofknowledge.com/')

    def test_mods_index_thematic_areas(self):
        """Teste índice MODS: áreas temáticas CAPES"""
        article = self._create_test_article()

        # Criar área temática hierárquica
        thematic_area = ThematicArea.objects.create(
            level0="Ciências da Saúde",
            level1="Medicina",
            level2="Clínica Médica",
            creator=self.user
        )

        # Relacionar com journal via ThematicAreaJournal
        ThematicAreaJournal.objects.create(
            journal=article.journal,
            thematic_area=thematic_area,
            creator=self.user
        )

        mods_subjects = self.index.prepare_mods_subject(article)
        self.assertEqual(len(mods_subjects), 1)

        subject = mods_subjects[0]

        # Deve usar level2 (mais específico)
        self.assertEqual(subject['topic']['text'], 'Clínica Médica')
        self.assertEqual(subject['topic']['authority'], 'capes-thematic-area')

    def test_mods_index_thematic_area_hierarchy(self):
        """Teste índice MODS: hierarquia de áreas temáticas"""
        article = self._create_test_article()

        # Área com apenas level1
        thematic_area1 = ThematicArea.objects.create(
            level0="Ciências Exatas",
            level1="Matemática",
            level2="",  # Vazio
            creator=self.user
        )

        # Área com apenas level0
        thematic_area2 = ThematicArea.objects.create(
            level0="Engenharias",
            level1="",  # Vazio
            level2="",  # Vazio
            creator=self.user
        )

        ThematicAreaJournal.objects.create(
            journal=article.journal,
            thematic_area=thematic_area1,
            creator=self.user
        )

        ThematicAreaJournal.objects.create(
            journal=article.journal,
            thematic_area=thematic_area2,
            creator=self.user
        )

        mods_subjects = self.index.prepare_mods_subject(article)
        self.assertEqual(len(mods_subjects), 2)

        subject_texts = [s['topic']['text'] for s in mods_subjects]

        # Deve usar level1 quando level2 está vazio
        self.assertIn('Matemática', subject_texts)

        # Deve usar level0 quando level1 e level2 estão vazios
        self.assertIn('Engenharias', subject_texts)

    def test_mods_index_toc_sections_relevant(self):
        """Teste índice MODS: seções TOC semanticamente relevantes"""
        article = self._create_test_article()

        # Seções relevantes (assuntos temáticos)
        relevant_section1 = self._create_test_toc_section("Artigos Originais")
        relevant_section2 = self._create_test_toc_section("Revisões Sistemáticas")

        # Seções estruturais (devem ser ignoradas)
        structural_section1 = self._create_test_toc_section("Editorial")
        structural_section2 = self._create_test_toc_section("Errata")

        article.toc_sections.add(
            relevant_section1, relevant_section2,
            structural_section1, structural_section2
        )

        mods_subjects = self.index.prepare_mods_subject(article)

        # Deve incluir apenas as seções relevantes
        self.assertEqual(len(mods_subjects), 2)

        subject_texts = [s['topic']['text'] for s in mods_subjects]
        self.assertIn('Artigos Originais', subject_texts)
        self.assertIn('Revisões Sistemáticas', subject_texts)

        # Não deve incluir seções estruturais
        self.assertNotIn('Editorial', subject_texts)
        self.assertNotIn('Errata', subject_texts)

        # Verificar autoridade TOC
        for subject in mods_subjects:
            self.assertEqual(subject['topic']['authority'], 'scielo-toc')

    def test_mods_index_toc_section_with_language(self):
        """Teste índice MODS: TOC section com idioma"""
        article = self._create_test_article()

        # TOC section em inglês
        toc_section_en = self._create_test_toc_section("Research Articles", self.language_en)
        article.toc_sections.add(toc_section_en)

        mods_subjects = self.index.prepare_mods_subject(article)
        self.assertEqual(len(mods_subjects), 1)

        subject = mods_subjects[0]
        self.assertEqual(subject['topic']['text'], 'Research Articles')
        self.assertEqual(subject['lang'], 'eng')  # en -> eng

    def test_mods_index_mixed_scenario_complete(self):
        """Teste índice MODS: cenário completo com todos os tipos de subject"""
        article = self._create_test_article()

        # 1. Keywords
        keyword1 = self._create_test_keyword("Diabetes Mellitus", self.vocabulary_decs)
        keyword2 = self._create_test_keyword("Machine Learning", self.vocabulary_mesh)
        article.keywords.add(keyword1, keyword2)

        # 2. Journal subject area
        subject_area = Subject.objects.create(
            value="Endocrinologia",
            creator=self.user
        )
        article.journal.subject.add(subject_area)

        # 3. Subject descriptor
        descriptor = SubjectDescriptor.objects.create(
            value="Metabolismo da Glicose",
            creator=self.user
        )
        article.journal.subject_descriptor.add(descriptor)

        # 4. WoS category
        wos_category = WebOfKnowledgeSubjectCategory.objects.create(
            value="Endocrinology & Metabolism",
            creator=self.user
        )
        article.journal.wos_area.add(wos_category)

        # 5. Thematic area
        thematic_area = ThematicArea.objects.create(
            level0="Ciências da Saúde",
            level1="Medicina",
            level2="Endocrinologia",
            creator=self.user
        )
        ThematicAreaJournal.objects.create(
            journal=article.journal,
            thematic_area=thematic_area,
            creator=self.user
        )

        # 6. TOC section relevante
        toc_section = self._create_test_toc_section("Artigos Originais")
        article.toc_sections.add(toc_section)

        mods_subjects = self.index.prepare_mods_subject(article)

        # Deve ter todos os tipos de subject (2 keywords + 5 do journal)
        self.assertEqual(len(mods_subjects), 7)

        # Verificar diversidade de autoridades
        authorities = [
            s['topic'].get('authority') if isinstance(s['topic'], dict) else None
            for s in mods_subjects
        ]
        authorities = [a for a in authorities if a]  # Remove None

        expected_authorities = {
            'decs', 'mesh', 'scielo-subject-area', 'scielo-descriptor',
            'wos', 'capes-thematic-area', 'scielo-toc'
        }

        for authority in expected_authorities:
            self.assertIn(authority, authorities,
                          f"Authority '{authority}' não encontrada nos subjects")

    def test_mods_index_empty_values_handling(self):
        """Teste índice MODS: tratamento de valores vazios"""
        article = self._create_test_article()

        # Subject area com valor vazio
        empty_subject = Subject.objects.create(
            value="",  # Vazio
            creator=self.user
        )
        article.journal.subject.add(empty_subject)

        # Área temática totalmente vazia
        empty_thematic = ThematicArea.objects.create(
            level0="",
            level1="",
            level2="",
            creator=self.user
        )
        ThematicAreaJournal.objects.create(
            journal=article.journal,
            thematic_area=empty_thematic,
            creator=self.user
        )

        mods_subjects = self.index.prepare_mods_subject(article)

        # Não deve incluir subjects com valores vazios
        self.assertEqual(len(mods_subjects), 0)

    def test_is_subject_relevant_section_edge_cases(self):
        """Teste função auxiliar: casos extremos de relevância de seções"""

        # Seções que devem ser excluídas
        irrelevant_sections = [
            "Editorial", "EDITORIAL", "editorial",
            "Erratum", "Errata", "ERRATA",
            "Instructions", "Instruções", "INSTRUÇÕES",
            "Nominata", "NOMINATA",
            "123",  # Apenas números
            "",  # Vazio
            "   ",  # Apenas espaços
        ]

        for section_text in irrelevant_sections:
            with self.subTest(section=section_text):
                is_relevant = self.index._is_subject_relevant_section(section_text)
                self.assertFalse(is_relevant,
                                 f"Seção '{section_text}' deveria ser irrelevante")

        # Seções que devem ser incluídas
        relevant_sections = [
            "Artigos Originais",
            "Research Articles",
            "Revisões Sistemáticas",
            "Case Reports",
            "Estudos Clínicos"
        ]

        for section_text in relevant_sections:
            with self.subTest(section=section_text):
                is_relevant = self.index._is_subject_relevant_section(section_text)
                self.assertTrue(is_relevant,
                                f"Seção '{section_text}' deveria ser relevante")

    def test_mods_index_article_without_journal(self):
        """Teste índice MODS: artigo sem journal"""
        article = Article.objects.create(
            pid_v2="S0000-00002024000100001",
            pid_v3=f'test-{uuid.uuid4().hex[:12]}',
            sps_pkg_name=f'test-{uuid.uuid4().hex[:12]}',
            article_type='research-article',
            creator=self.user
        )

        # Adicionar apenas keyword
        keyword = self._create_test_keyword("Test Keyword")
        article.keywords.add(keyword)

        mods_subjects = self.index.prepare_mods_subject(article)

        # Deve ter apenas a keyword (sem subjects do journal)
        self.assertEqual(len(mods_subjects), 1)
        self.assertEqual(mods_subjects[0]['topic']['text'], 'Test Keyword')

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_subject.MODSSubjectTestCase -v 2
