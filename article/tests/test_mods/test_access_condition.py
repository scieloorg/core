import uuid
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from article.models import Article
from article.search_indexes import ArticleOAIMODSIndex
from collection.models import Collection
from core.models import Language, License, LicenseStatement
from issue.models import Issue
from journal.models import Journal, OfficialJournal, JournalLicense, SciELOJournal
from location.models import Location, City, State, Country

User = get_user_model()


class MODSAccessConditionTestCase(TransactionTestCase):
    """
    Testes unitários focados no índice MODS para elemento accessCondition
    Testa todos os tipos de condições de acesso do ecossistema SciELO
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

        # Criar coleções
        self.collection_scl = Collection.objects.create(
            acron3="scl",
            acron2="br",
            code="001",
            domain="www.scielo.br",
            main_name="SciELO Brasil",
            collection_type="journals",
            is_active=True,
            creator=self.user
        )

        self.collection_arg = Collection.objects.create(
            acron3="arg",
            acron2="ar",
            code="002",
            domain="www.scielo.org.ar",
            main_name="SciELO Argentina",
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

        # Criar SciELOJournal para testes de collection
        self.scielo_journal = SciELOJournal.objects.create(
            collection=self.collection_scl,
            journal=self.journal,
            journal_acron="rbm",
            issn_scielo="0100-1234",
            creator=self.user
        )

        self.index = ArticleOAIMODSIndex()

    def tearDown(self):
        """Limpeza após cada teste"""
        Article.objects.all().delete()
        LicenseStatement.objects.all().delete()
        License.objects.all().delete()
        JournalLicense.objects.all().delete()
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
        """Teste índice MODS: artigo sem licenças"""
        article = self._create_test_article()

        access_conditions = self.index.prepare_mods_access_condition(article)

        # Pode ter políticas de coleção, mas não licenças específicas
        self.assertIsInstance(access_conditions, list)

    def test_access_condition_journal_license_basic(self):
        """Teste índice MODS: licença específica do journal (JournalLicense)"""
        article = self._create_test_article()

        # Criar licença específica do journal (NÃO Creative Commons para testar autoridade básica)
        journal_license = self._create_journal_license("MIT License")
        article.journal.journal_use_license = journal_license
        article.journal.save()

        access_conditions = self.index.prepare_mods_access_condition(article)

        # Deve ter pelo menos a licença do journal
        self.assertGreaterEqual(len(access_conditions), 1)

        # Encontrar a condição de licença
        license_condition = None
        for condition in access_conditions:
            if condition.get('type') == 'use and reproduction':
                license_condition = condition
                break

        self.assertIsNotNone(license_condition)
        self.assertEqual(license_condition['text'], 'MIT License')
        self.assertEqual(license_condition['authority'], 'scielo-journal-license')

    def test_access_condition_creative_commons_detection(self):
        """Teste índice MODS: detecção automática de Creative Commons"""
        article = self._create_test_article()

        # Licenças Creative Commons com diferentes formatos (respeitando limite de 16 chars)
        cc_licenses = [
            "CC BY 4.0",
            "cc-by-sa",
            "CC-BY-NC",
            "attribution"
        ]

        for cc_license in cc_licenses:
            with self.subTest(license=cc_license):
                # Limpar licença anterior
                article.journal.journal_use_license = None
                article.journal.save()

                journal_license = self._create_journal_license(cc_license)
                article.journal.journal_use_license = journal_license
                article.journal.save()

                access_conditions = self.index.prepare_mods_access_condition(article)

                # Encontrar condição CC
                cc_condition = None
                for condition in access_conditions:
                    if condition.get('authority') == 'creativecommons':
                        cc_condition = condition
                        break

                self.assertIsNotNone(cc_condition, f"CC não detectado para: {cc_license}")
                self.assertEqual(cc_condition['authority'], 'creativecommons')
                self.assertEqual(cc_condition['authorityURI'], 'https://creativecommons.org/')
                self.assertEqual(cc_condition['displayLabel'], 'Creative Commons License')

    def test_access_condition_core_license_fallback(self):
        """Teste índice MODS: fallback para License do core"""
        article = self._create_test_article()

        # Criar apenas licença do core (não do journal)
        core_license = self._create_core_license("MIT License")
        article.journal.use_license = core_license
        article.journal.save()

        access_conditions = self.index.prepare_mods_access_condition(article)

        # Deve usar a licença do core
        license_condition = None
        for condition in access_conditions:
            if condition.get('type') == 'use and reproduction':
                license_condition = condition
                break

        self.assertIsNotNone(license_condition)
        self.assertEqual(license_condition['text'], 'MIT License')
        self.assertEqual(license_condition['authority'], 'scielo-core-license')

    def test_access_condition_license_priority(self):
        """Teste índice MODS: prioridade entre licenças"""
        article = self._create_test_article()

        # Criar ambas as licenças
        journal_license = self._create_journal_license("CC BY 4.0")
        core_license = self._create_core_license("MIT License")

        article.journal.journal_use_license = journal_license
        article.journal.use_license = core_license
        article.journal.save()

        access_conditions = self.index.prepare_mods_access_condition(article)

        # Deve priorizar journal_use_license
        license_texts = [c['text'] for c in access_conditions if c.get('type') == 'use and reproduction']

        self.assertIn('CC BY 4.0', license_texts)
        self.assertNotIn('MIT License', license_texts)  # Não deve usar fallback

    def test_access_condition_open_access_status(self):
        """Teste índice MODS: status de Open Access"""
        oa_status_tests = [
            ("diamond", None),  # Sem restrições
            ("gold", None),  # Sem restrições
            ("hybrid", "Hybrid open access model - some content may require subscription"),
            ("bronze", "Bronze open access - free to read but with copyright restrictions"),
            ("green", "Green open access - author self-archived version available"),
            ("closed", "Subscription required for full access")
        ]

        for oa_status, expected_restriction in oa_status_tests:
            with self.subTest(oa_status=oa_status):
                article = self._create_test_article()

                article.journal.open_access = oa_status
                article.journal.save()

                access_conditions = self.index.prepare_mods_access_condition(article)

                if expected_restriction:
                    # Deve ter restrição de acesso
                    restriction_conditions = [
                        c for c in access_conditions
                        if c.get('type') == 'restriction on access'
                    ]
                    self.assertGreater(len(restriction_conditions), 0)

                    # Verificar se a restrição específica está presente
                    restriction_texts = [c['text'] for c in restriction_conditions]
                    self.assertIn(expected_restriction, restriction_texts)

                    # Verificar metadados
                    for condition in restriction_conditions:
                        if condition['text'] == expected_restriction:
                            self.assertEqual(condition['authority'], 'scielo-oa-model')
                            self.assertEqual(condition['displayLabel'], f'Open Access Model: {oa_status.title()}')

    def test_access_condition_collection_policies(self):
        """Teste índice MODS: políticas das coleções"""
        article = self._create_test_article()

        # Simular que o artigo tem collections (isso dependeria da implementação real)
        # Por ora, testamos apenas a lógica da função

        # Testar política conhecida
        policy_scl = self.index._get_collection_policy(self.collection_scl)
        self.assertEqual(policy_scl, 'Open access following SciELO Brazil editorial criteria')

        # Testar política argentina
        policy_arg = self.index._get_collection_policy(self.collection_arg)
        self.assertEqual(policy_arg, 'Open access following SciELO Argentina editorial criteria')

        # Testar coleção desconhecida
        collection_unknown = Collection.objects.create(
            acron3="xyz",
            main_name="Unknown Collection",
            collection_type="journals",
            creator=self.user
        )
        policy_unknown = self.index._get_collection_policy(collection_unknown)
        self.assertIsNone(policy_unknown)

    def test_access_condition_mixed_scenario(self):
        """Teste índice MODS: cenário completo com múltiplas condições"""
        article = self._create_test_article()

        # 1. Licença Creative Commons (limite de 16 chars)
        cc_license = self._create_journal_license("CC BY-SA 4.0")
        article.journal.journal_use_license = cc_license

        # 2. Status Open Access restritivo
        article.journal.open_access = "hybrid"
        article.journal.save()

        access_conditions = self.index.prepare_mods_access_condition(article)

        # Deve ter pelo menos 2 condições: licença + restrição OA
        self.assertGreaterEqual(len(access_conditions), 2)

        # Verificar licença CC
        cc_conditions = [c for c in access_conditions if c.get('authority') == 'creativecommons']
        self.assertEqual(len(cc_conditions), 1)
        self.assertEqual(cc_conditions[0]['text'], 'CC BY-SA 4.0')

        # Verificar restrição OA
        oa_restrictions = [c for c in access_conditions if c.get('authority') == 'scielo-oa-model']
        self.assertEqual(len(oa_restrictions), 1)
        self.assertIn('Hybrid open access', oa_restrictions[0]['text'])

    def test_access_condition_creative_commons_vs_regular_authority(self):
        """Teste específico: autoridade Creative Commons vs regular"""
        article = self._create_test_article()

        # Teste 1: Licença regular (não CC)
        regular_license = self._create_journal_license("MIT License")
        article.journal.journal_use_license = regular_license
        article.journal.save()

        access_conditions = self.index.prepare_mods_access_condition(article)
        regular_condition = next(
            (c for c in access_conditions if c.get('type') == 'use and reproduction'),
            None
        )

        self.assertIsNotNone(regular_condition)
        self.assertEqual(regular_condition['authority'], 'scielo-journal-license')
        self.assertNotIn('authorityURI', regular_condition)

        # Teste 2: Licença Creative Commons
        cc_license = self._create_journal_license("CC BY 4.0")
        article.journal.journal_use_license = cc_license
        article.journal.save()

        access_conditions = self.index.prepare_mods_access_condition(article)
        cc_condition = next(
            (c for c in access_conditions if c.get('type') == 'use and reproduction'),
            None
        )

        self.assertIsNotNone(cc_condition)
        self.assertEqual(cc_condition['authority'], 'creativecommons')
        self.assertEqual(cc_condition['authorityURI'], 'https://creativecommons.org/')
        self.assertEqual(cc_condition['displayLabel'], 'Creative Commons License')

    def test_access_condition_empty_values_handling(self):
        """Teste índice MODS: tratamento de valores vazios"""
        article = self._create_test_article()

        # Licença com tipo vazio
        empty_license = JournalLicense.objects.create(
            license_type="",  # Vazio
            creator=self.user
        )
        article.journal.journal_use_license = empty_license

        # Open access vazio
        article.journal.open_access = ""
        article.journal.save()

        access_conditions = self.index.prepare_mods_access_condition(article)

        # Não deve incluir condições com valores vazios
        license_conditions = [c for c in access_conditions if c.get('type') == 'use and reproduction']
        self.assertEqual(len(license_conditions), 0)

    def test_is_creative_commons_license_edge_cases(self):
        """Teste função auxiliar: detecção de Creative Commons - casos extremos"""

        # Casos que devem ser detectados como CC (respeitando limite de 16 chars)
        cc_cases = [
            "CC BY",
            "cc by",
            "CC-BY",
            "cc-by-sa",
            "Attribution",
            "CCby"
        ]

        for license_text in cc_cases:
            with self.subTest(license=license_text):
                is_cc = self.index._is_creative_commons_license(license_text)
                self.assertTrue(is_cc, f"'{license_text}' deveria ser detectado como CC")

        # Casos que NÃO devem ser detectados como CC
        non_cc_cases = [
            "MIT License",
            "Apache 2.0",
            "GPL v3",
            "Proprietary",
            "All Rights",  # Truncado para caber em 16 chars
            "",
            None
        ]

        for license_text in non_cc_cases:
            with self.subTest(license=license_text):
                is_cc = self.index._is_creative_commons_license(license_text)
                self.assertFalse(is_cc, f"'{license_text}' NÃO deveria ser detectado como CC")

    def test_access_condition_article_without_journal(self):
        """Teste índice MODS: artigo sem journal"""
        article = Article.objects.create(
            pid_v2="S0000-00002024000100001",
            pid_v3=f'test-{uuid.uuid4().hex[:12]}',
            sps_pkg_name=f'test-{uuid.uuid4().hex[:12]}',
            article_type='research-article',
            creator=self.user
        )

        access_conditions = self.index.prepare_mods_access_condition(article)

        # Deve retornar lista vazia ou apenas políticas gerais
        self.assertIsInstance(access_conditions, list)

        # Não deve ter licenças específicas
        license_conditions = [c for c in access_conditions if c.get('type') == 'use and reproduction']
        self.assertEqual(len(license_conditions), 0)

    def test_safe_get_collections_error_handling(self):
        """Teste função auxiliar: tratamento seguro de erros ao obter collections"""
        article = self._create_test_article()

        # Testar com objeto normal
        collections = self.index._safe_get_collections(article)
        self.assertIsInstance(collections, list)

        # Testar com objeto None
        collections_none = self.index._safe_get_collections(None)
        self.assertEqual(collections_none, [])

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_access_condition.MODSAccessConditionTestCase -v 2
