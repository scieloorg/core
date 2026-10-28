"""
Um Article por CollectionPidV2 (XML + coleção, mesmo pid v3): filtros por
coleção, relatórios por coleção, um documento por Article no índice de
busca e vínculo entre as instâncias do mesmo artigo no OAI.
"""
from importlib import import_module

from django.contrib.auth import get_user_model
from django.test import TestCase

from article.models import Article
from article.search_indexes import ArticleIndex, ArticleOAIIndex
from article.tests.test_mixins import make_article_in_collection
from collection.models import Collection
from journal.models import Journal, SciELOJournal
from report import data_availability

User = get_user_model()

PID_V3 = "CVcmNHzKpFmYM77VQBJwHYt"
PID_V2_SCL = "S0103-65642009000300003"
PID_V2_PSI = "S1678-51772009000300003"


class ArticleByCollectionDataMixin:
    """
    Psicologia USP: scl (pusp, 0103-6564) e psi (psicousp, 1678-5177)
    Journal Single: somente scl (single, 0000-0001)
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="by-collection", password="x")
        cls.scl = Collection.objects.create(
            acron3="scl",
            network_classification=["scielonetwork"],
            domain="www.scielo.br",
            is_active=True,
            creator=cls.user,
        )
        cls.psi = Collection.objects.create(
            acron3="psi",
            domain="pepsic.bvsalud.org",
            is_active=True,
            creator=cls.user,
        )
        cls.pusp = Journal.objects.create(title="Psicologia USP", creator=cls.user)
        cls.single = Journal.objects.create(title="Journal Single", creator=cls.user)
        for journal, collection, acron, issn_scielo in (
            (cls.pusp, cls.scl, "pusp", "0103-6564"),
            (cls.pusp, cls.psi, "psicousp", "1678-5177"),
            (cls.single, cls.scl, "single", "0000-0001"),
        ):
            SciELOJournal.objects.create(
                journal=journal,
                collection=collection,
                journal_acron=acron,
                issn_scielo=issn_scielo,
                creator=cls.user,
            )
        cls.scl_item = make_article_in_collection(
            cls.user, PID_V3, cls.scl, PID_V2_SCL, "pusp",
            journal=cls.pusp, is_classic_public=True,
        )
        cls.psi_item = make_article_in_collection(
            cls.user, PID_V3, cls.psi, PID_V2_PSI, "psicousp",
            journal=cls.pusp, is_classic_public=True,
        )


class SelectItemsByCollectionTest(ArticleByCollectionDataMixin, TestCase):
    def test_collection_acron_list(self):
        self.assertEqual(
            set(Article.select_items(collection_acron_list=["psi"])),
            {self.psi_item},
        )
        self.assertEqual(
            set(Article.select_items(collection_acron_list=["scl", "psi"])),
            {self.scl_item, self.psi_item},
        )

    def test_journal_acron_of_the_collection(self):
        self.assertEqual(
            set(Article.select_items(journal_acron_list=["psicousp"])),
            {self.psi_item},
        )
        self.assertEqual(
            set(Article.select_items(journal_acron_list=["pusp"])),
            {self.scl_item},
        )

    def test_journal_acron_and_collection(self):
        self.assertEqual(
            list(Article.select_items(
                collection_acron_list=["scl"], journal_acron_list=["psicousp"]
            )),
            [],
        )

    def test_data_availability_report_counts_by_collection(self):
        for collection, expected in ((self.scl, 1), (self.psi, 1), (None, 2)):
            qs = data_availability.filter_articles(collection=collection)
            self.assertEqual(qs.count(), expected, collection)


class ArticleIndexByCollectionTest(ArticleByCollectionDataMixin, TestCase):
    """Um documento por Article (coleção), relacionados pelo pid v3."""

    def test_index_queryset_has_one_item_by_collection(self):
        self.assertEqual(
            set(ArticleIndex().index_queryset()), {self.scl_item, self.psi_item}
        )

    def test_collection_fields_of_the_article_collection(self):
        index = ArticleIndex()
        self.assertEqual(index.prepare_collection(self.psi_item), ["psi"])
        self.assertEqual(index.prepare_ids(self.psi_item)[:2], [PID_V2_PSI, PID_V3])
        self.assertEqual(index.prepare_ta_cluster(self.psi_item), ["psicousp"])

    def test_oai_identifier_has_collection(self):
        index = ArticleOAIIndex()
        self.assertEqual(
            index.prepare_id(self.psi_item), f"oai:scielo:psi_{PID_V2_PSI}"
        )
        self.assertEqual(
            index.prepare_item_id(self.scl_item), f"oai:scielo:scl_{PID_V2_SCL}"
        )
        self.assertEqual(index.prepare_collections(self.psi_item), {"1678-5177"})

    def test_identical_items_urls(self):
        self.assertEqual(
            self.scl_item.identical_items_urls,
            [f"{self.psi.base_url}/scielo.php?script=sci_arttext&pid={PID_V2_PSI}"],
        )

    def test_oai_compile_relates_identical_items(self):
        compiled = ArticleOAIIndex().fields["compile"].prepare(self.scl_item)
        self.assertIn('<element name="isidenticalto">', compiled)
        self.assertIn(
            f"{self.psi.base_url}/scielo.php?script=sci_arttext&amp;pid={PID_V2_PSI}",
            compiled,
        )
        self.assertIn(
            f'<field name="identifier">scl_{PID_V2_SCL}</field>', compiled
        )
        self.assertIn(f'<field name="identifier">{PID_V3}</field>', compiled)
        # o identificador local vem primeiro
        self.assertLess(
            compiled.index(f"scl_{PID_V2_SCL}</field>"),
            compiled.index(f'<field name="identifier">{PID_V3}</field>'),
        )
        # identificadores pid v2 e pid v3 qualificados
        self.assertRegex(
            compiled,
            r'<element name="pidv2">\s*<element>\s*<field name="value">'
            + PID_V2_SCL
            + "</field>",
        )
        self.assertRegex(
            compiled,
            r'<element name="pidv3">\s*<element>\s*<field name="value">'
            + PID_V3
            + "</field>",
        )


class MigrationIdentifyCollectionTest(TestCase):
    """article.0054: identificação da coleção dos artigos"""

    def setUp(self):
        self.migration = import_module(
            "article.migrations.0054_migrate_article_collection_pid_v2"
        )
        main = ["scielonetwork"]
        self.journal_collections = {
            # periódico em uma coleção
            1: [{"collection_id": 10, "issn_scielo": "0000-0001",
                 "journal_acron": "single", "collection__network_classification": main}],
            # issn_scielo diferente em cada coleção
            2: [
                {"collection_id": 10, "issn_scielo": "0103-6564",
                 "journal_acron": "pusp", "collection__network_classification": main},
                {"collection_id": 20, "issn_scielo": "1678-5177",
                 "journal_acron": "psicousp", "collection__network_classification": None},
            ],
            # mesmo issn_scielo nas duas coleções
            3: [
                {"collection_id": 20, "issn_scielo": "0102-311X",
                 "journal_acron": "csp", "collection__network_classification": None},
                {"collection_id": 10, "issn_scielo": "0102-311X",
                 "journal_acron": "csp", "collection__network_classification": main},
            ],
            # mesmo issn_scielo, nenhuma coleção principal
            4: [
                {"collection_id": 20, "issn_scielo": "0254-9247",
                 "journal_acron": "rp", "collection__network_classification": None},
                {"collection_id": 30, "issn_scielo": "0254-9247",
                 "journal_acron": "rp", "collection__network_classification": None},
            ],
        }

    def identify(self, journal_id, pid_v2=None, collection_id=None):
        return self.migration.identify_collection_id(
            {"journal_id": journal_id, "pid_v2": pid_v2, "collection_id": collection_id},
            self.journal_collections,
        )

    def test_article_collection(self):
        self.assertEqual(self.identify(2, PID_V2_SCL, collection_id=20), 20)

    def test_single_collection_journal(self):
        self.assertEqual(self.identify(1), 10)

    def test_issn_scielo_of_pid_v2(self):
        self.assertEqual(self.identify(2, PID_V2_SCL), 10)
        self.assertEqual(self.identify(2, PID_V2_PSI), 20)

    def test_same_issn_scielo_uses_main_collection(self):
        self.assertEqual(self.identify(3, "S0102-311X2019000104001"), 10)

    def test_not_identified(self):
        self.assertIsNone(self.identify(4, "S0254-92472019000104001"))
