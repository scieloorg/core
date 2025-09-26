import uuid
from django.test import TestCase
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


class MODSSubjectTestCase(TestCase):
    """
    Testes unitários otimizados para elemento subject MODS
    Testa todos os tipos de assuntos do ecossistema SciELO
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

        # Criar vocabulários base
        cls.vocabulary_decs = Vocabulary.objects.create(
            name="Health Science Descriptors",
            acronym="decs",
            creator=cls.user
        )

        cls.vocabulary_mesh = Vocabulary.objects.create(
            name="Medical Subject Headings",
            acronym="mesh",
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
        cls.collection = Collection.objects.create(
            acron3="scl",
            acron2="br",
            code="001",
            domain="www.scielo.br",
            main_name="SciELO Brasil",
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

        # Criar issue
        cls.issue = Issue.objects.create(
            journal=cls.journal,
            volume="10",
            number="2",
            year="2024",
            creator=cls.user
        )

        # Pré-criar objetos de subject para journal
        cls.subject_area = Subject.objects.create(
            code="medicina",
            value="Medicina",
            creator=cls.user
        )

        cls.subject_descriptor = SubjectDescriptor.objects.create(
            value="Endocrinologia",
            creator=cls.user
        )

        cls.wos_category = WebOfKnowledgeSubjectCategory.objects.create(
            value="Medicine, General & Internal",
            creator=cls.user
        )

        cls.thematic_area = ThematicArea.objects.create(
            level0="Ciências da Saúde",
            level1="Medicina",
            level2="Clínica Médica",
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

    def _create_test_keyword(self, text, vocabulary=None, language=None):
        """Helper para criar keyword de teste"""
        return Keyword.objects.create(
            text=text,
            vocabulary=vocabulary,
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

    def test_subject_no_subjects(self):
        """Teste: artigo sem subjects"""
        article = self._create_test_article()

        mods_subjects = self.index.prepare_mods_subject(article)

        self.assertEqual(len(mods_subjects), 0)

    def test_subject_single_keyword_basic(self):
        """Teste: keyword básico sem vocabulário controlado"""
        article = self._create_test_article()

        # Keyword explicitamente sem vocabulário
        keyword = self._create_test_keyword("Diabetes", vocabulary=None)
        article.keywords.add(keyword)

        mods_subjects = self.index.prepare_mods_subject(article)

        self.assertEqual(len(mods_subjects), 1)

        subject = mods_subjects[0]
        self.assertEqual(subject['topic'], 'Diabetes')
        self.assertEqual(subject['lang'], 'por')

    def test_subject_keyword_with_vocabulary_authority(self):
        """Teste: keyword com vocabulário controlado"""
        article = self._create_test_article()

        keyword = self._create_test_keyword("Hypertension", vocabulary=self.vocabulary_mesh)
        article.keywords.add(keyword)

        mods_subjects = self.index.prepare_mods_subject(article)

        self.assertEqual(len(mods_subjects), 1)

        subject = mods_subjects[0]
        self.assertIsInstance(subject['topic'], dict)
        self.assertEqual(subject['topic']['text'], 'Hypertension')
        self.assertEqual(subject['topic']['authority'], 'mesh')

    def test_subject_multiple_keywords_variations(self):
        """Teste: múltiplas keywords com diferentes configurações"""
        article = self._create_test_article()

        keyword_test_cases = [
            ("Diabetes", self.vocabulary_decs, self.language_pt, 'por'),
            ("Machine Learning", self.vocabulary_mesh, self.language_en, 'eng'),
            ("Inteligência Artificial", None, self.language_pt, 'por'),
        ]

        # Criar keywords
        for text, vocabulary, language, expected_lang in keyword_test_cases:
            keyword = self._create_test_keyword(text, vocabulary, language)
            article.keywords.add(keyword)

        mods_subjects = self.index.prepare_mods_subject(article)
        self.assertEqual(len(mods_subjects), 3)

        # Validar cada keyword
        subjects_by_text = {}
        for subject in mods_subjects:
            if isinstance(subject['topic'], str):
                subjects_by_text[subject['topic']] = subject
            else:
                subjects_by_text[subject['topic']['text']] = subject

        # Verificar casos específicos
        for text, vocabulary, language, expected_lang in keyword_test_cases:
            with self.subTest(keyword=text):
                subject = subjects_by_text[text]
                self.assertEqual(subject['lang'], expected_lang)

                if vocabulary:
                    self.assertIsInstance(subject['topic'], dict)
                    self.assertEqual(subject['topic']['authority'], vocabulary.acronym)

    def test_subject_journal_subject_types(self):
        """Teste: diferentes tipos de subject do journal"""
        article = self._create_test_article()

        # Configurar diferentes tipos de subject no journal
        article.journal.subject.add(self.subject_area)
        article.journal.subject_descriptor.add(self.subject_descriptor)
        article.journal.wos_area.add(self.wos_category)

        # Adicionar área temática
        ThematicAreaJournal.objects.create(
            journal=article.journal,
            thematic_area=self.thematic_area,
            creator=self.user
        )

        mods_subjects = self.index.prepare_mods_subject(article)
        self.assertEqual(len(mods_subjects), 4)

        # Validar autoridades específicas
        authority_mappings = {
            'Medicina': 'scielo-subject-area',
            'Endocrinologia': 'scielo-descriptor',
            'Medicine, General & Internal': 'wos',
            'Clínica Médica': 'capes-thematic-area',
        }

        subjects_by_text = {s['topic']['text']: s for s in mods_subjects}

        for text, expected_authority in authority_mappings.items():
            with self.subTest(subject=text):
                subject = subjects_by_text[text]
                self.assertEqual(subject['topic']['authority'], expected_authority)

    def test_subject_wos_category_with_uri(self):
        """Teste: categoria WoS com authorityURI"""
        article = self._create_test_article()
        article.journal.wos_area.add(self.wos_category)

        mods_subjects = self.index.prepare_mods_subject(article)

        wos_subject = mods_subjects[0]
        self.assertEqual(wos_subject['topic']['authority'], 'wos')
        self.assertEqual(wos_subject['topic']['authorityURI'], 'http://apps.webofknowledge.com/')

    def test_subject_thematic_area_hierarchy(self):
        """Teste: hierarquia de áreas temáticas"""
        article = self._create_test_article()

        hierarchy_test_cases = [
            # (level0, level1, level2, expected_result)
            ("Ciências da Saúde", "Medicina", "Clínica Médica", "Clínica Médica"),
            ("Ciências Exatas", "Matemática", "", "Matemática"),
            ("Engenharias", "", "", "Engenharias"),
        ]

        for level0, level1, level2, expected in hierarchy_test_cases:
            with self.subTest(hierarchy=f"{level0}/{level1}/{level2}"):
                # Criar área temática específica
                thematic_area = ThematicArea.objects.create(
                    level0=level0,
                    level1=level1,
                    level2=level2,
                    creator=self.user
                )

                # Criar journal específico para evitar conflitos
                journal = Journal.objects.create(
                    official=self.official_journal,
                    title=f"Test Journal {uuid.uuid4().hex[:8]}",
                    creator=self.user
                )

                ThematicAreaJournal.objects.create(
                    journal=journal,
                    thematic_area=thematic_area,
                    creator=self.user
                )

                test_article = self._create_test_article(journal=journal)
                mods_subjects = self.index.prepare_mods_subject(test_article)

                self.assertEqual(len(mods_subjects), 1)
                subject = mods_subjects[0]
                self.assertEqual(subject['topic']['text'], expected)
                self.assertEqual(subject['topic']['authority'], 'capes-thematic-area')

    def test_subject_toc_sections_relevance(self):
        """Teste: relevância de seções TOC"""
        article = self._create_test_article()

        toc_section_cases = [
            # (text, language, should_be_included)
            ("Artigos Originais", self.language_pt, True),
            ("Research Articles", self.language_en, True),
            ("Editorial", self.language_pt, False),
            ("Errata", self.language_pt, False),
            ("Instructions", self.language_en, False),
        ]

        # Criar todas as seções
        for text, language, should_be_included in toc_section_cases:
            toc_section = self._create_test_toc_section(text, language)
            article.toc_sections.add(toc_section)

        mods_subjects = self.index.prepare_mods_subject(article)

        # Contar quantas seções devem ser incluídas
        expected_count = sum(1 for _, _, should_include in toc_section_cases if should_include)
        self.assertEqual(len(mods_subjects), expected_count)

        # Verificar conteúdo das seções incluídas
        included_texts = [s['topic']['text'] for s in mods_subjects]

        for text, language, should_be_included in toc_section_cases:
            if should_be_included:
                self.assertIn(text, included_texts)
            else:
                self.assertNotIn(text, included_texts)

        # Verificar autoridade TOC
        for subject in mods_subjects:
            self.assertEqual(subject['topic']['authority'], 'scielo-toc')

    def test_subject_edge_cases_handling(self):
        """Teste: casos extremos e valores vazios"""
        article = self._create_test_article()

        edge_cases = [
            ('empty_subject_area', lambda: Subject.objects.create(value="", creator=self.user)),
            ('empty_thematic_area', lambda: ThematicArea.objects.create(
                level0="", level1="", level2="", creator=self.user
            )),
            ('empty_keyword', lambda: self._create_test_keyword("")),
        ]

        for case_name, creator_func in edge_cases:
            with self.subTest(case=case_name):
                # Limpar subjects anteriores
                article.keywords.clear()
                article.journal.subject.clear()
                ThematicAreaJournal.objects.filter(journal=article.journal).delete()

                # Criar objeto com problema
                obj = creator_func()

                if case_name == 'empty_subject_area':
                    article.journal.subject.add(obj)
                elif case_name == 'empty_thematic_area':
                    ThematicAreaJournal.objects.create(
                        journal=article.journal,
                        thematic_area=obj,
                        creator=self.user
                    )
                elif case_name == 'empty_keyword':
                    article.keywords.add(obj)

                mods_subjects = self.index.prepare_mods_subject(article)

                # Para keywords vazias, pode retornar subject com texto vazio
                # Para outros casos, valores vazios não devem aparecer
                if case_name == 'empty_keyword':
                    # Keyword vazia pode aparecer, mas com texto vazio
                    if mods_subjects:
                        topic = mods_subjects[0]['topic']
                        topic_text = topic if isinstance(topic, str) else topic.get('text', '')
                        self.assertEqual(topic_text.strip(), '')
                else:
                    self.assertEqual(len(mods_subjects), 0)

    def test_subject_complete_scenario(self):
        """Teste: cenário completo com todos os tipos de subject"""
        article = self._create_test_article()

        # 1. Keywords com diferentes vocabulários
        keyword1 = self._create_test_keyword("Diabetes Mellitus", self.vocabulary_decs)
        keyword2 = self._create_test_keyword("Machine Learning", self.vocabulary_mesh)
        article.keywords.add(keyword1, keyword2)

        # 2. Configurar todos os tipos de subject do journal
        article.journal.subject.add(self.subject_area)
        article.journal.subject_descriptor.add(self.subject_descriptor)
        article.journal.wos_area.add(self.wos_category)

        ThematicAreaJournal.objects.create(
            journal=article.journal,
            thematic_area=self.thematic_area,
            creator=self.user
        )

        # 3. TOC section relevante
        toc_section = self._create_test_toc_section("Artigos Originais")
        article.toc_sections.add(toc_section)

        mods_subjects = self.index.prepare_mods_subject(article)

        # Deve ter todos os tipos (2 keywords + 4 journal subjects + 1 toc)
        self.assertEqual(len(mods_subjects), 7)

        # Verificar diversidade de autoridades
        authorities = set()
        for subject in mods_subjects:
            if isinstance(subject['topic'], dict):
                authorities.add(subject['topic']['authority'])

        expected_authorities = {
            'decs', 'mesh', 'scielo-subject-area', 'scielo-descriptor',
            'wos', 'capes-thematic-area', 'scielo-toc'
        }

        self.assertEqual(authorities, expected_authorities)

    def test_subject_relevance_function_edge_cases(self):
        """Teste: função de relevância de seções com casos extremos"""
        irrelevant_patterns = [
            "Editorial", "EDITORIAL", "editorial",
            "Erratum", "Errata", "ERRATA",
            "Instructions", "Instruções", "INSTRUÇÕES",
            "Nominata", "NOMINATA",
            "123",  # Apenas números
            "",  # Vazio
            "   ",  # Apenas espaços
        ]

        relevant_patterns = [
            "Artigos Originais",
            "Research Articles",
            "Revisões Sistemáticas",
            "Case Reports",
            "Estudos Clínicos"
        ]

        # Testar padrões irrelevantes
        for pattern in irrelevant_patterns:
            with self.subTest(irrelevant=pattern):
                is_relevant = self.index._is_subject_relevant_section(pattern)
                self.assertFalse(is_relevant)

        # Testar padrões relevantes
        for pattern in relevant_patterns:
            with self.subTest(relevant=pattern):
                is_relevant = self.index._is_subject_relevant_section(pattern)
                self.assertTrue(is_relevant)

    def test_subject_article_without_journal(self):
        """Teste: artigo sem journal (apenas keywords próprias)"""
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

        subject = mods_subjects[0]
        # A estrutura pode ser string simples ou dict com text
        if isinstance(subject['topic'], str):
            self.assertEqual(subject['topic'], 'Test Keyword')
        else:
            self.assertEqual(subject['topic']['text'], 'Test Keyword')

    def test_subject_language_code_mapping(self):
        """Teste: mapeamento correto de códigos de idioma"""
        article = self._create_test_article()

        language_mappings = [
            (self.language_pt, 'por'),  # pt -> por
            (self.language_en, 'eng'),  # en -> eng
        ]

        for language, expected_code in language_mappings:
            with self.subTest(language=language.code2):
                # Limpar keywords anteriores
                article.keywords.clear()

                keyword = self._create_test_keyword("Test", language=language)
                article.keywords.add(keyword)

                mods_subjects = self.index.prepare_mods_subject(article)

                self.assertEqual(len(mods_subjects), 1)
                subject = mods_subjects[0]
                self.assertEqual(subject['lang'], expected_code)

    def test_subject_structure_consistency_validation(self):
        """Teste: validação de consistência da estrutura subject"""
        article = self._create_test_article()

        # Adicionar diferentes tipos para testar estrutura
        keyword = self._create_test_keyword("Test Keyword", self.vocabulary_decs)
        article.keywords.add(keyword)
        article.journal.wos_area.add(self.wos_category)

        mods_subjects = self.index.prepare_mods_subject(article)

        # Validar estrutura de cada subject
        for subject in mods_subjects:
            self.assertIsInstance(subject, dict)
            self.assertIn('topic', subject)

            # Campo lang pode não estar presente em todos os casos
            # Verificar apenas se presente
            if 'lang' in subject:
                self.assertIsInstance(subject['lang'], str)

            # Validar estrutura do topic
            topic = subject['topic']
            if isinstance(topic, dict):
                self.assertIn('text', topic)
                self.assertIn('authority', topic)
                if topic['authority'] == 'wos':
                    self.assertIn('authorityURI', topic)
            else:
                self.assertIsInstance(topic, str)

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_subject.MODSSubjectTestCase --parallel 2 -v 2
