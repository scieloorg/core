import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from article.models import Article
from article.search_indexes import ArticleOAIMODSIndex
from collection.models import Collection
from core.models import Language, License
from issue.models import Issue
from journal.models import Journal, OfficialJournal, JournalLicense, SciELOJournal

User = get_user_model()


class MODSAccessConditionTestCase(TestCase):
    """
    Testes unitários otimizados para elemento accessCondition MODS
    Testa condições de acesso do ecossistema SciELO
    """

    @classmethod
    def setUpTestData(cls):
        """Dados compartilhados entre testes para melhor performance"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

        # Criar idiomas uma vez
        cls.language_pt = Language.objects.create(
            name="Portuguese",
            code2="pt",
            creator=cls.user
        )

        # Criar coleções
        cls.collection_scl = Collection.objects.create(
            acron3="scl",
            acron2="br",
            domain="www.scielo.br",
            main_name="SciELO Brasil",
            collection_type="journals",
            is_active=True,
            creator=cls.user
        )

        cls.collection_arg = Collection.objects.create(
            acron3="arg",
            acron2="ar",
            domain="www.scielo.org.ar",
            main_name="SciELO Argentina",
            collection_type="journals",
            is_active=True,
            creator=cls.user
        )

        # Journal setup
        cls.official_journal = OfficialJournal.objects.create(
            title="Revista Brasileira de Medicina",
            issn_print="0100-1234",
            issn_electronic="1678-5678",
            issnl="0100-1234",
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

        cls.scielo_journal = SciELOJournal.objects.create(
            collection=cls.collection_scl,
            journal=cls.journal,
            journal_acron="rbm",
            issn_scielo="0100-1234",
            creator=cls.user
        )

    def setUp(self):
        """Configuração mínima por teste"""
        self.index = ArticleOAIMODSIndex()

    def _create_test_article(self, **kwargs):
        """Helper otimizado para criar artigo"""
        defaults = {
            'pid_v3': f'test-{uuid.uuid4().hex[:8]}',
            'article_type': 'research-article',
            'journal': self.journal,
            'issue': self.issue,
            'creator': self.user
        }
        defaults.update(kwargs)
        return Article.objects.create(**defaults)

    def _create_journal_license(self, license_type):
        """Helper para criar JournalLicense"""
        return JournalLicense.objects.create(
            license_type=license_type,
            creator=self.user
        )

    def _create_core_license(self, license_type):
        """Helper para criar License do core"""
        return License.objects.create(
            license_type=license_type,
            creator=self.user
        )

    def test_access_condition_no_licenses(self):
        """Teste: artigo sem licenças"""
        article = self._create_test_article()

        access_conditions = self.index.prepare_mods_access_condition(article)

        self.assertIsInstance(access_conditions, list)

    def test_access_condition_journal_license_basic(self):
        """Teste: licença específica do journal"""
        article = self._create_test_article()

        journal_license = self._create_journal_license("MIT License")
        article.journal.journal_use_license = journal_license
        article.journal.save()

        access_conditions = self.index.prepare_mods_access_condition(article)

        # Deve ter licença
        license_conditions = [c for c in access_conditions if c.get('type') == 'use and reproduction']
        self.assertGreaterEqual(len(license_conditions), 1)

        license_condition = license_conditions[0]
        self.assertEqual(license_condition['text'], 'MIT License')
        self.assertEqual(license_condition['authority'], 'scielo-journal-license')

    def test_access_condition_creative_commons_detection(self):
        """Teste: detecção automática de Creative Commons"""
        article = self._create_test_article()

        cc_licenses = ["CC BY 4.0", "cc-by-sa", "CC-BY-NC", "attribution"]

        for cc_license in cc_licenses:
            with self.subTest(license=cc_license):
                # Reset journal
                article.journal.journal_use_license = None
                article.journal.save()

                journal_license = self._create_journal_license(cc_license)
                article.journal.journal_use_license = journal_license
                article.journal.save()

                access_conditions = self.index.prepare_mods_access_condition(article)

                cc_conditions = [c for c in access_conditions if c.get('authority') == 'creativecommons']
                self.assertEqual(len(cc_conditions), 1, f"CC não detectado para: {cc_license}")

                cc_condition = cc_conditions[0]
                self.assertEqual(cc_condition['authority'], 'creativecommons')
                self.assertEqual(cc_condition['authorityURI'], 'https://creativecommons.org/')
                self.assertEqual(cc_condition['displayLabel'], 'Creative Commons License')

    def test_access_condition_core_license_fallback(self):
        """Teste: fallback para License do core"""
        article = self._create_test_article()

        core_license = self._create_core_license("MIT License")
        article.journal.use_license = core_license
        article.journal.save()

        access_conditions = self.index.prepare_mods_access_condition(article)

        license_conditions = [c for c in access_conditions if c.get('type') == 'use and reproduction']
        self.assertGreaterEqual(len(license_conditions), 1)

        license_condition = license_conditions[0]
        self.assertEqual(license_condition['text'], 'MIT License')
        self.assertEqual(license_condition['authority'], 'scielo-core-license')

    def test_access_condition_license_priority(self):
        """Teste: prioridade entre licenças"""
        article = self._create_test_article()

        journal_license = self._create_journal_license("CC BY 4.0")
        core_license = self._create_core_license("MIT License")

        article.journal.journal_use_license = journal_license
        article.journal.use_license = core_license
        article.journal.save()

        access_conditions = self.index.prepare_mods_access_condition(article)

        license_texts = [c['text'] for c in access_conditions if c.get('type') == 'use and reproduction']

        # Deve priorizar journal_use_license
        self.assertIn('CC BY 4.0', license_texts)
        self.assertNotIn('MIT License', license_texts)

    def test_access_condition_open_access_status(self):
        """Teste: status de Open Access"""
        oa_tests = [
            ("diamond", None),
            ("gold", None),
            ("hybrid", "Hybrid open access model - some content may require subscription"),
            ("bronze", "Bronze open access - free to read but with copyright restrictions"),
            ("green", "Green open access - author self-archived version available"),
            ("closed", "Subscription required for full access")
        ]

        for oa_status, expected_restriction in oa_tests:
            with self.subTest(oa_status=oa_status):
                article = self._create_test_article()

                article.journal.open_access = oa_status
                article.journal.save()

                access_conditions = self.index.prepare_mods_access_condition(article)

                if expected_restriction:
                    restrictions = [c for c in access_conditions if c.get('type') == 'restriction on access']
                    self.assertGreater(len(restrictions), 0)

                    restriction_texts = [c['text'] for c in restrictions]
                    self.assertIn(expected_restriction, restriction_texts)

                    # Verificar metadados
                    matching_condition = next(c for c in restrictions if c['text'] == expected_restriction)
                    self.assertEqual(matching_condition['authority'], 'scielo-oa-model')
                    self.assertEqual(matching_condition['displayLabel'], f'Open Access Model: {oa_status.title()}')

    def test_access_condition_collection_policies(self):
        """Teste: políticas das coleções"""
        # Testar políticas diretamente
        policy_scl = self.index._get_collection_policy(self.collection_scl)
        self.assertEqual(policy_scl, 'Open access following SciELO Brazil editorial criteria')

        policy_arg = self.index._get_collection_policy(self.collection_arg)
        self.assertEqual(policy_arg, 'Open access following SciELO Argentina editorial criteria')

        # Coleção desconhecida
        unknown_collection = Collection.objects.create(
            acron3="xyz",
            main_name="Unknown Collection",
            collection_type="journals",
            creator=self.user
        )
        policy_unknown = self.index._get_collection_policy(unknown_collection)
        self.assertIsNone(policy_unknown)

    def test_access_condition_mixed_scenario(self):
        """Teste: cenário com licença CC + OA status"""
        article = self._create_test_article()

        cc_license = self._create_journal_license("CC BY-SA 4.0")
        article.journal.journal_use_license = cc_license
        article.journal.open_access = "hybrid"
        article.journal.save()

        access_conditions = self.index.prepare_mods_access_condition(article)

        # Deve ter licença + restrição OA
        self.assertGreaterEqual(len(access_conditions), 2)

        cc_conditions = [c for c in access_conditions if c.get('authority') == 'creativecommons']
        oa_restrictions = [c for c in access_conditions if c.get('authority') == 'scielo-oa-model']

        self.assertEqual(len(cc_conditions), 1)
        self.assertEqual(cc_conditions[0]['text'], 'CC BY-SA 4.0')

        self.assertEqual(len(oa_restrictions), 1)
        self.assertIn('Hybrid open access', oa_restrictions[0]['text'])

    def test_access_condition_creative_commons_vs_regular(self):
        """Teste: diferença entre CC e licença regular"""
        article = self._create_test_article()

        # Licença regular
        regular_license = self._create_journal_license("MIT License")
        article.journal.journal_use_license = regular_license
        article.journal.save()

        access_conditions = self.index.prepare_mods_access_condition(article)
        regular_condition = next(
            (c for c in access_conditions if c.get('type') == 'use and reproduction'), None
        )

        self.assertIsNotNone(regular_condition)
        self.assertEqual(regular_condition['authority'], 'scielo-journal-license')
        self.assertNotIn('authorityURI', regular_condition)

        # Licença Creative Commons
        cc_license = self._create_journal_license("CC BY 4.0")
        article.journal.journal_use_license = cc_license
        article.journal.save()

        access_conditions = self.index.prepare_mods_access_condition(article)
        cc_condition = next(
            (c for c in access_conditions if c.get('type') == 'use and reproduction'), None
        )

        self.assertIsNotNone(cc_condition)
        self.assertEqual(cc_condition['authority'], 'creativecommons')
        self.assertEqual(cc_condition['authorityURI'], 'https://creativecommons.org/')

    def test_access_condition_empty_values(self):
        """Teste: tratamento de valores vazios"""
        article = self._create_test_article()

        # Licença vazia
        empty_license = self._create_journal_license("")
        article.journal.journal_use_license = empty_license
        article.journal.open_access = ""
        article.journal.save()

        access_conditions = self.index.prepare_mods_access_condition(article)

        license_conditions = [c for c in access_conditions if c.get('type') == 'use and reproduction']
        self.assertEqual(len(license_conditions), 0)

    def test_is_creative_commons_detection_cases(self):
        """Teste: casos extremos de detecção CC"""
        cc_cases = ["CC BY", "cc by", "CC-BY", "cc-by-sa", "Attribution", "CCby"]
        non_cc_cases = ["MIT License", "Apache 2.0", "GPL v3", "Proprietary", "", None]

        for license_text in cc_cases:
            with self.subTest(license=license_text):
                is_cc = self.index._is_creative_commons_license(license_text)
                self.assertTrue(is_cc, f"'{license_text}' deveria ser CC")

        for license_text in non_cc_cases:
            with self.subTest(license=license_text):
                is_cc = self.index._is_creative_commons_license(license_text)
                self.assertFalse(is_cc, f"'{license_text}' NÃO deveria ser CC")

    def test_access_condition_article_without_journal(self):
        """Teste: artigo sem journal"""
        article = Article.objects.create(
            pid_v3=f'test-{uuid.uuid4().hex[:8]}',
            article_type='research-article',
            creator=self.user
        )

        access_conditions = self.index.prepare_mods_access_condition(article)

        self.assertIsInstance(access_conditions, list)

        license_conditions = [c for c in access_conditions if c.get('type') == 'use and reproduction']
        self.assertEqual(len(license_conditions), 0)

    def test_safe_get_collections_error_handling(self):
        """Teste: tratamento seguro de collections"""
        article = self._create_test_article()

        collections = self.index._safe_get_collections(article)
        self.assertIsInstance(collections, list)

        collections_none = self.index._safe_get_collections(None)
        self.assertEqual(collections_none, [])

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_access_condition.MODSAccessConditionTestCase --parallel 2 -v 2
