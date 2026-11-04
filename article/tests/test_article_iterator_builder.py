import logging
import unittest
from unittest.mock import MagicMock, call, patch

from django.db.models import Q

# Ajuste este caminho se a classe estiver em outro módulo.
MODULE_PATH = "article.controller"
from article.controller import ArticleIteratorBuilder  # noqa: E402


def setUpModule():
    """
    Desliga o logging (abaixo de CRITICAL) para todo o módulo de testes.

    Sem isso, logging.info/logging.error chamados dentro de
    ArticleIteratorBuilder alcançam os handlers reais configurados no
    settings.LOGGING do Django (ex.: handler que despacha para o
    OpenSearch de forma assíncrona) — em ambiente de teste esse host
    normalmente não existe/não está acessível, gerando ruído de
    "NameResolutionError" / "--- Logging error ---" no output dos testes.
    """
    logging.disable(logging.CRITICAL)


def tearDownModule():
    logging.disable(logging.NOTSET)


# =======================================================================
# Helpers
# =======================================================================
def make_builder(**kwargs):
    defaults = dict(
        user=MagicMock(name="user"),
        collection_acron_list=None,
        journal_acron_list=None,
        from_pub_year=None,
        until_pub_year=None,
        from_date=None,
        until_date=None,
        force_update=None,
        limit=None,
        timeout=None,
        opac_url=None,
    )
    defaults.update(kwargs)
    return ArticleIteratorBuilder(**defaults)


class FakeValuesQuerySet:
    """
    Simula o resultado final de .values(...)/.values(...=F(...)) — os
    itens já são os dicts finais, e .iterator() apenas os devolve.
    """

    def __init__(self, items):
        self.items = list(items)

    def values(self, *args, **kwargs):
        return self

    def distinct(self):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def iterator(self):
        return iter(self.items)


class FakeArticleBaseQuerySet:
    """
    Simula o `base_qs` de from_article: .filter(pp_xml__isnull=False)
    registra os kwargs recebidos (para asserção) e devolve a própria
    instância, permitindo encadear .values(...).iterator().
    """

    def __init__(self, items=None):
        self._items = list(items or [])
        self.received_filter_kwargs = None

    def filter(self, **kwargs):
        self.received_filter_kwargs = kwargs
        return self

    def values(self, *args, **kwargs):
        return self

    def iterator(self):
        return iter(self._items)


# =======================================================================
# __init__
# =======================================================================
class TestInit(unittest.TestCase):
    def test_stores_common_attributes(self):
        user = MagicMock(name="user")
        builder = ArticleIteratorBuilder(
            user=user,
            collection_acron_list=["scl"],
            journal_acron_list=["abc"],
            from_pub_year=2020,
            until_pub_year=2022,
            from_date="2020-01-01",
            until_date="2022-12-31",
            force_update=True,
            limit=10,
            timeout=30,
            opac_url="www.custom.br",
        )
        self.assertIs(builder.user, user)
        self.assertEqual(builder.collection_acron_list, ["scl"])
        self.assertEqual(builder.journal_acron_list, ["abc"])
        self.assertEqual(builder.from_pub_year, 2020)
        self.assertEqual(builder.until_pub_year, 2022)
        self.assertEqual(builder.from_date, "2020-01-01")
        self.assertEqual(builder.until_date, "2022-12-31")
        self.assertTrue(builder.force_update)
        self.assertEqual(builder.limit, 10)
        self.assertEqual(builder.timeout, 30)
        self.assertEqual(builder.opac_url, "www.custom.br")

    def test_defaults_are_none(self):
        builder = ArticleIteratorBuilder(user=MagicMock())
        self.assertIsNone(builder.collection_acron_list)
        self.assertIsNone(builder.journal_acron_list)
        self.assertIsNone(builder.from_pub_year)
        self.assertIsNone(builder.until_pub_year)
        self.assertIsNone(builder.from_date)
        self.assertIsNone(builder.until_date)
        self.assertIsNone(builder.force_update)
        self.assertIsNone(builder.limit)
        self.assertIsNone(builder.timeout)
        self.assertIsNone(builder.opac_url)

    def test_source_specific_filters_are_not_instance_attributes(self):
        """
        proc_status_list / data_status_list / article_source_status_list
        são exclusivos de cada fonte e não devem existir como atributo de
        instância (ficam só como parâmetro do método correspondente).
        """
        builder = make_builder()
        self.assertFalse(hasattr(builder, "proc_status_list"))
        self.assertFalse(hasattr(builder, "data_status_list"))
        self.assertFalse(hasattr(builder, "article_source_status_list"))


# =======================================================================
# from_pid_provider
# =======================================================================
class TestFromPidProvider(unittest.TestCase):
    def test_yields_dicts_directly_from_queryset(self):
        builder = make_builder()
        items = [{"pp_xml_id": 1}, {"pp_xml_id": 2}]

        with patch(f"{MODULE_PATH}.PidProviderXML") as MockPPX:
            (
                MockPPX.objects.filter.return_value
                .order_by.return_value
                .values.return_value
                .distinct.return_value
            ) = FakeValuesQuerySet(items)

            result = list(builder.from_pid_provider())

        self.assertEqual(result, items)

    def test_default_proc_status_used_when_not_provided(self):
        builder = make_builder()

        with patch(f"{MODULE_PATH}.PidProviderXML") as MockPPX, \
             patch(f"{MODULE_PATH}.pid_provider_choices") as MockChoices:
            MockChoices.PPXML_STATUS_TODO = "todo"
            (
                MockPPX.objects.filter.return_value
                .order_by.return_value
                .values.return_value
                .distinct.return_value
            ) = FakeValuesQuerySet([])

            list(builder.from_pid_provider())

            _, kwargs = MockPPX.objects.filter.call_args
            self.assertEqual(kwargs["proc_status__in"], ["todo"])

    def test_custom_proc_status_list_used_when_provided(self):
        builder = make_builder()

        with patch(f"{MODULE_PATH}.PidProviderXML") as MockPPX:
            (
                MockPPX.objects.filter.return_value
                .order_by.return_value
                .values.return_value
                .distinct.return_value
            ) = FakeValuesQuerySet([])

            list(builder.from_pid_provider(proc_status_list=["custom"]))

            _, kwargs = MockPPX.objects.filter.call_args
            self.assertEqual(kwargs["proc_status__in"], ["custom"])

    def test_date_and_year_filters_applied(self):
        builder = make_builder(
            from_pub_year=2020,
            until_pub_year=2022,
            from_date="2020-01-01",
            until_date="2022-12-31",
        )

        with patch(f"{MODULE_PATH}.PidProviderXML") as MockPPX:
            (
                MockPPX.objects.filter.return_value
                .order_by.return_value
                .values.return_value
                .distinct.return_value
            ) = FakeValuesQuerySet([])

            list(builder.from_pid_provider())

            _, kwargs = MockPPX.objects.filter.call_args
            self.assertEqual(kwargs["pub_year__gte"], 2020)
            self.assertEqual(kwargs["pub_year__lte"], 2022)
            self.assertEqual(kwargs["updated__gte"], "2020-01-01")
            self.assertEqual(kwargs["updated__lte"], "2022-12-31")

    def test_no_collection_or_journal_filter_skips_scielojournal_query(self):
        """
        Sem collection_acron_list nem journal_acron_list, `params` fica
        vazio e SciELOJournal não deve ser consultado; `q` permanece um
        Q() vazio.
        """
        builder = make_builder()

        with patch(f"{MODULE_PATH}.PidProviderXML") as MockPPX, \
             patch(f"{MODULE_PATH}.SciELOJournal") as MockSciELOJournal:
            (
                MockPPX.objects.filter.return_value
                .order_by.return_value
                .values.return_value
                .distinct.return_value
            ) = FakeValuesQuerySet([])

            list(builder.from_pid_provider())

            MockSciELOJournal.objects.select_related.assert_not_called()
            (q_arg,), _ = MockPPX.objects.filter.call_args
            self.assertFalse(q_arg)  # Q() vazio é falsy

    def test_collection_acron_list_alone_queries_scielojournal(self):
        builder = make_builder(collection_acron_list=["scl"])

        with patch(f"{MODULE_PATH}.PidProviderXML") as MockPPX, \
             patch(f"{MODULE_PATH}.SciELOJournal") as MockSciELOJournal:
            sj_mock = MockSciELOJournal.objects.select_related.return_value
            sj_mock.filter.return_value.values_list.return_value.distinct.return_value = [
                ("1234-5678", "8765-4321"),
            ]
            (
                MockPPX.objects.filter.return_value
                .order_by.return_value
                .values.return_value
                .distinct.return_value
            ) = FakeValuesQuerySet([{"pp_xml_id": 1}])

            result = list(builder.from_pid_provider())

        sj_mock.filter.assert_called_once_with(collection__acron3__in=["scl"])
        self.assertEqual(result, [{"pp_xml_id": 1}])

    def test_journal_acron_list_alone_queries_scielojournal(self):
        builder = make_builder(journal_acron_list=["abc"])

        with patch(f"{MODULE_PATH}.PidProviderXML") as MockPPX, \
             patch(f"{MODULE_PATH}.SciELOJournal") as MockSciELOJournal:
            sj_mock = MockSciELOJournal.objects.select_related.return_value
            sj_mock.filter.return_value.values_list.return_value.distinct.return_value = [
                ("1234-5678", None),
            ]
            (
                MockPPX.objects.filter.return_value
                .order_by.return_value
                .values.return_value
                .distinct.return_value
            ) = FakeValuesQuerySet([])

            list(builder.from_pid_provider())

        sj_mock.filter.assert_called_once_with(journal_acron__in=["abc"])

    def test_collection_and_journal_combined_in_single_filter_call(self):
        builder = make_builder(
            collection_acron_list=["scl"], journal_acron_list=["abc"]
        )

        with patch(f"{MODULE_PATH}.PidProviderXML") as MockPPX, \
             patch(f"{MODULE_PATH}.SciELOJournal") as MockSciELOJournal:
            sj_mock = MockSciELOJournal.objects.select_related.return_value
            sj_mock.filter.return_value.values_list.return_value.distinct.return_value = []
            (
                MockPPX.objects.filter.return_value
                .order_by.return_value
                .values.return_value
                .distinct.return_value
            ) = FakeValuesQuerySet([])

            list(builder.from_pid_provider())

        sj_mock.filter.assert_called_once_with(
            collection__acron3__in=["scl"], journal_acron__in=["abc"]
        )

    def test_issn_list_filters_out_falsy_values(self):
        builder = make_builder(journal_acron_list=["abc"])

        with patch(f"{MODULE_PATH}.PidProviderXML") as MockPPX, \
             patch(f"{MODULE_PATH}.SciELOJournal") as MockSciELOJournal:
            sj_mock = MockSciELOJournal.objects.select_related.return_value
            # Um periódico só com issn_print, outro só com issn_electronic,
            # outro com ambos nulos (deve ser ignorado).
            sj_mock.filter.return_value.values_list.return_value.distinct.return_value = [
                ("1111-1111", None),
                (None, "2222-2222"),
                (None, None),
            ]
            (
                MockPPX.objects.filter.return_value
                .order_by.return_value
                .values.return_value
                .distinct.return_value
            ) = FakeValuesQuerySet([])

            list(builder.from_pid_provider())

            (q_arg,), _ = MockPPX.objects.filter.call_args
            q_str = str(q_arg)
            self.assertIn("1111-1111", q_str)
            self.assertIn("2222-2222", q_str)

    def test_no_issn_found_still_queries_pidproviderxml(self):
        """
        Diferente de uma implementação anterior: aqui NÃO há early-return
        quando SciELOJournal não encontra nenhum ISSN — o código monta um
        Q(issn_print__in=set())|Q(issn_electronic__in=set()) (que não
        casa com nada) e segue para PidProviderXML.objects.filter mesmo
        assim.
        """
        builder = make_builder(journal_acron_list=["nao-existe"])

        with patch(f"{MODULE_PATH}.PidProviderXML") as MockPPX, \
             patch(f"{MODULE_PATH}.SciELOJournal") as MockSciELOJournal:
            sj_mock = MockSciELOJournal.objects.select_related.return_value
            sj_mock.filter.return_value.values_list.return_value.distinct.return_value = []
            (
                MockPPX.objects.filter.return_value
                .order_by.return_value
                .values.return_value
                .distinct.return_value
            ) = FakeValuesQuerySet([])

            list(builder.from_pid_provider())

        MockPPX.objects.filter.assert_called_once()


# =======================================================================
# from_article
# =======================================================================
class TestFromArticle(unittest.TestCase):
    def test_no_data_status_list_means_no_filter_key(self):
        builder = make_builder()
        base_qs = FakeArticleBaseQuerySet()

        with patch(f"{MODULE_PATH}.Article") as MockArticle:
            MockArticle.objects.filter.return_value.distinct.return_value = base_qs

            list(builder.from_article())

            _, kwargs = MockArticle.objects.filter.call_args
            self.assertNotIn("data_status__in", kwargs)

    def test_data_status_list_included_when_provided(self):
        builder = make_builder()
        base_qs = FakeArticleBaseQuerySet()

        with patch(f"{MODULE_PATH}.Article") as MockArticle:
            MockArticle.objects.filter.return_value.distinct.return_value = base_qs

            list(builder.from_article(data_status_list=["pending", "invalid"]))

            _, kwargs = MockArticle.objects.filter.call_args
            self.assertEqual(kwargs["data_status__in"], ["pending", "invalid"])

    def test_valid_false_always_applied(self):
        builder = make_builder()
        base_qs = FakeArticleBaseQuerySet()

        with patch(f"{MODULE_PATH}.Article") as MockArticle:
            MockArticle.objects.filter.return_value.distinct.return_value = base_qs

            list(builder.from_article())

            _, kwargs = MockArticle.objects.filter.call_args
            self.assertIs(kwargs["valid"], False)

    def test_collection_and_journal_filters_traverse_scielojournal_join(self):
        builder = make_builder(
            collection_acron_list=["scl"], journal_acron_list=["abc"]
        )
        base_qs = FakeArticleBaseQuerySet()

        with patch(f"{MODULE_PATH}.Article") as MockArticle:
            MockArticle.objects.filter.return_value.distinct.return_value = base_qs

            list(builder.from_article())

            _, kwargs = MockArticle.objects.filter.call_args
            self.assertEqual(
                kwargs["journal__scielojournal__collection__acron3__in"], ["scl"]
            )
            self.assertEqual(
                kwargs["journal__scielojournal__journal_acron__in"], ["abc"]
            )

    def test_pub_year_and_date_filters_applied(self):
        builder = make_builder(
            from_pub_year=2019,
            until_pub_year=2021,
            from_date="2019-01-01",
            until_date="2021-12-31",
        )
        base_qs = FakeArticleBaseQuerySet()

        with patch(f"{MODULE_PATH}.Article") as MockArticle:
            MockArticle.objects.filter.return_value.distinct.return_value = base_qs

            list(builder.from_article())

            _, kwargs = MockArticle.objects.filter.call_args
            self.assertEqual(kwargs["pub_date_year__gte"], 2019)
            self.assertEqual(kwargs["pub_date_year__lte"], 2021)
            self.assertEqual(kwargs["updated__gte"], "2019-01-01")
            self.assertEqual(kwargs["updated__lte"], "2021-12-31")

    def test_only_articles_with_pp_xml_are_yielded(self):
        builder = make_builder()
        items = [{"pp_xml_id": 10}, {"pp_xml_id": 20}]
        base_qs = FakeArticleBaseQuerySet(items)

        with patch(f"{MODULE_PATH}.Article") as MockArticle:
            MockArticle.objects.filter.return_value.distinct.return_value = base_qs

            result = list(builder.from_article())

        self.assertEqual(base_qs.received_filter_kwargs, {"pp_xml__isnull": False})
        self.assertEqual(result, items)


# =======================================================================
# from_article_source
# =======================================================================
class TestFromArticleSource(unittest.TestCase):
    def test_yields_dicts_directly_from_queryset(self):
        builder = make_builder(from_date="d1", until_date="d2", force_update=False)
        items = [{"article_source_id": 10}, {"article_source_id": 20}]

        with patch(f"{MODULE_PATH}.ArticleSource") as MockArticleSource, \
             patch(f"{MODULE_PATH}.pid_provider_choices") as MockChoices:
            MockChoices.PPXML_STATUS_TO_CREATE_OR_UPDATE_ARTICLE_SOURCE = "to_create"
            (
                MockArticleSource.objects.filter.return_value.values.return_value
            ) = FakeValuesQuerySet(items)

            result = list(
                builder.from_article_source(article_source_status_list=["pending"])
            )

        self.assertEqual(result, items)

    def test_force_update_uses_empty_q(self):
        builder = make_builder(force_update=True)

        with patch(f"{MODULE_PATH}.ArticleSource") as MockArticleSource:
            (
                MockArticleSource.objects.filter.return_value.values.return_value
            ) = FakeValuesQuerySet([])

            list(builder.from_article_source())

            (q_arg,), _ = MockArticleSource.objects.filter.call_args
            self.assertFalse(q_arg)


# =======================================================================
# from_harvest
# =======================================================================
class TestFromHarvest(unittest.TestCase):
    def test_loads_collection_when_empty(self):
        builder = make_builder()

        with patch(f"{MODULE_PATH}.Collection") as MockCollection:
            MockCollection.objects.count.return_value = 0
            MockCollection.objects.values_list.return_value.distinct.return_value = []

            list(builder.from_harvest())

        MockCollection.load.assert_called_once_with(builder.user)

    def test_does_not_load_collection_when_not_empty(self):
        builder = make_builder()

        with patch(f"{MODULE_PATH}.Collection") as MockCollection:
            MockCollection.objects.count.return_value = 5
            MockCollection.objects.values_list.return_value.distinct.return_value = []

            list(builder.from_harvest())

        MockCollection.load.assert_not_called()

    def test_uses_collection_acron_list_when_given(self):
        builder = make_builder(collection_acron_list=["scl", "mex"])

        with patch(f"{MODULE_PATH}.Collection") as MockCollection:
            MockCollection.objects.count.return_value = 5
            with patch.object(
                builder, "_build_harvesters", return_value=[]
            ) as mock_build:
                list(builder.from_harvest())

        MockCollection.objects.values_list.assert_not_called()
        self.assertEqual(mock_build.call_args_list, [call("scl"), call("mex")])

    def test_uses_all_collections_when_collection_acron_list_absent(self):
        builder = make_builder()

        with patch(f"{MODULE_PATH}.Collection") as MockCollection:
            MockCollection.objects.count.return_value = 5
            MockCollection.objects.values_list.return_value.distinct.return_value = [
                "scl", "mex"
            ]
            with patch.object(
                builder, "_build_harvesters", return_value=[]
            ) as mock_build:
                list(builder.from_harvest())

        MockCollection.objects.values_list.assert_called_once_with("acron3", flat=True)
        self.assertEqual(mock_build.call_args_list, [call("scl"), call("mex")])

    def test_yields_expected_dict_from_documents(self):
        builder = make_builder(collection_acron_list=["scl"])
        doc = {
            "url": "http://x/y.xml",
            "pid_v2": "S123",
            "processing_date": "2024-01-01",
            "is_public": True,
        }

        with patch(f"{MODULE_PATH}.Collection") as MockCollection:
            MockCollection.objects.count.return_value = 5

            fake_harvester = MagicMock()
            fake_harvester.harvest_documents.return_value = [doc]
            with patch.object(
                builder, "_build_harvesters", return_value=[fake_harvester]
            ):
                result = list(builder.from_harvest())

        self.assertEqual(result, [{
            "xml_url": "http://x/y.xml",
            "collection_acron": "scl",
            "pid": "S123",
            "source_date": "2024-01-01",
            "is_public": True,
            "document": {
                "url": "http://x/y.xml",
                "pid_v2": "S123",
                "processing_date": "2024-01-01",
                "is_public": True,
            },
        }])

    def test_uses_origin_date_when_processing_date_absent(self):
        builder = make_builder(collection_acron_list=["scl"])
        doc = {
            "url": "http://x/y.xml",
            "pid_v2": "S123",
            "origin_date": "2023-05-05",
            "is_public": False,
        }

        with patch(f"{MODULE_PATH}.Collection") as MockCollection:
            MockCollection.objects.count.return_value = 5

            fake_harvester = MagicMock()
            fake_harvester.harvest_documents.return_value = [doc]
            with patch.object(
                builder, "_build_harvesters", return_value=[fake_harvester]
            ):
                result = list(builder.from_harvest())

        self.assertEqual(result[0]["source_date"], "2023-05-05")


# =======================================================================
# _build_harvesters
# =======================================================================
class TestBuildHarvesters(unittest.TestCase):
    def test_scl_collection_uses_opac_harvester_with_default_url(self):
        builder = make_builder(
            opac_url=None, from_date="a", until_date="b", limit=10, timeout=30
        )

        with patch(f"{MODULE_PATH}.OPACHarvester") as MockOPACHarvester:
            result = list(builder._build_harvesters("scl"))

        MockOPACHarvester.assert_called_once_with(
            "https://www.scielo.br", "scl", from_date="a", until_date="b",
            limit=10, timeout=30,
        )
        self.assertEqual(result, [MockOPACHarvester.return_value])

    def test_scl_collection_uses_provided_opac_url(self):
        builder = make_builder(opac_url="www.custom.br")

        with patch(f"{MODULE_PATH}.OPACHarvester") as MockOPACHarvester:
            list(builder._build_harvesters("scl"))

        args, _ = MockOPACHarvester.call_args
        self.assertEqual(args[0], "www.custom.br")

    def test_opac_url_applies_to_any_collection(self):
        builder = make_builder(opac_url="https://www.scielo.org.mx")

        with patch(f"{MODULE_PATH}.OPACHarvester") as MockOPACHarvester, \
             patch(f"{MODULE_PATH}.AMHarvester") as MockAMHarvester:
            list(builder._build_harvesters("mex"))

        MockOPACHarvester.assert_called_once_with("https://www.scielo.org.mx", "mex")
        MockAMHarvester.assert_not_called()

    def test_opac_with_journal_acron_list_builds_harvester_per_journal(self):
        builder = make_builder(journal_acron_list=["abc", "def"])

        with patch(f"{MODULE_PATH}.OPACHarvester") as MockOPACHarvester:
            result = list(builder._build_harvesters("scl"))

        self.assertEqual(
            MockOPACHarvester.call_args_list,
            [
                call("https://www.scielo.br", "scl", journal="abc"),
                call("https://www.scielo.br", "scl", journal="def"),
            ],
        )
        self.assertEqual(len(result), 2)

    def test_opac_passes_stop(self):
        builder = make_builder(stop=100)

        with patch(f"{MODULE_PATH}.OPACHarvester") as MockOPACHarvester:
            list(builder._build_harvesters("scl"))

        _, kwargs = MockOPACHarvester.call_args
        self.assertEqual(kwargs["stop"], 100)

    def test_non_scl_collection_uses_am_harvester(self):
        builder = make_builder(from_date="a", until_date="b", limit=5, timeout=15)

        with patch(f"{MODULE_PATH}.AMHarvester") as MockAMHarvester, \
             patch(f"{MODULE_PATH}.SciELOJournal") as MockSciELOJournal:
            result = list(builder._build_harvesters("mex"))

        MockAMHarvester.assert_called_once_with(
            "article", "mex", from_date="a", until_date="b", limit=5, timeout=15
        )
        MockSciELOJournal.objects.filter.assert_not_called()
        self.assertEqual(result, [MockAMHarvester.return_value])

    def test_non_scl_collection_without_journal_acron_list_has_no_journal_kwarg(self):
        builder = make_builder()

        with patch(f"{MODULE_PATH}.AMHarvester") as MockAMHarvester:
            list(builder._build_harvesters("mex"))

        _, kwargs = MockAMHarvester.call_args
        self.assertNotIn("journal", kwargs)

    def test_articlemeta_builds_harvester_per_issn_scielo(self):
        builder = make_builder(journal_acron_list=["abc", "def"])

        with patch(f"{MODULE_PATH}.AMHarvester") as MockAMHarvester, \
             patch(f"{MODULE_PATH}.SciELOJournal") as MockSciELOJournal:
            (
                MockSciELOJournal.objects.filter.return_value
                .exclude.return_value
                .values_list.return_value
                .distinct.return_value
            ) = ["1234-5678", "8765-4321"]
            result = list(builder._build_harvesters("mex"))

        MockSciELOJournal.objects.filter.assert_called_once_with(
            collection__acron3="mex", journal_acron__in=["abc", "def"]
        )
        self.assertEqual(
            MockAMHarvester.call_args_list,
            [
                call("article", "mex", journal="1234-5678"),
                call("article", "mex", journal="8765-4321"),
            ],
        )
        self.assertEqual(len(result), 2)


# =======================================================================
# OPACHarvester (counter_dict v2)
# =======================================================================
class TestOPACHarvester(unittest.TestCase):
    HARVESTER_PATH = "core.utils.harvesters"

    def make_item(self, aid, **kwargs):
        item = {
            "aid": aid,
            "journal_acronym": "abc",
            "pid": "S1234-56782024000100001",
            "pid_v1": "",
            "pid_v2": "S1234-56782024000100001",
            "pid_v3": aid,
            "publication_date": "2024-01-31",
            "default_language": "pt",
            "is_public": True,
            "created": "2024-01-10T08:00:00.000000",
            "updated": "2024-01-31T10:30:15.654000",
        }
        item.update(kwargs)
        return item

    def harvest(self, responses, **kwargs):
        from core.utils.harvesters import OPACHarvester

        harvester = OPACHarvester("https://www.scielo.br", "scl", **kwargs)
        with patch(
            f"{self.HARVESTER_PATH}.fetch_data", side_effect=responses
        ) as mock_fetch:
            documents = list(harvester.harvest_documents())
        return documents, [c.args[0] for c in mock_fetch.call_args_list]

    def test_requests_counter_dict_v2(self):
        _, urls = self.harvest(
            [{"pages": 0, "documents": []}],
            from_date="2024-01-31T10:30:00-03:00",
            until_date="2024-02-01",
            limit=10,
            journal="abc",
        )
        self.assertEqual(
            urls,
            [
                "https://www.scielo.br/api/v2/counter_dict?"
                "begin_date=2024-01-31T10%3A30%3A00-03%3A00"
                "&end_date=2024-02-01&limit=10&journal=abc&page=1"
            ],
        )

    def test_default_until_date_has_time(self):
        from core.utils.harvesters import OPACHarvester

        harvester = OPACHarvester()
        self.assertEqual(len(harvester.until_date), len("2024-01-31T10:30:15"))

    def test_documents_list_with_full_updated_date(self):
        documents, urls = self.harvest(
            [
                {"pages": 2, "documents": [self.make_item("aid1")]},
                {
                    "pages": 2,
                    "documents": [
                        self.make_item("aid2", updated=None),
                        self.make_item("", journal_acronym="abc"),
                    ],
                },
            ]
        )
        self.assertEqual(len(urls), 2)
        self.assertEqual([d["pid_v3"] for d in documents], ["aid1", "aid2"])

        doc = documents[0]
        self.assertEqual(doc["url"], "https://www.scielo.br/j/abc/a/aid1/?format=xml")
        self.assertEqual(doc["origin_date"], "2024-01-31")
        self.assertEqual(doc["updated"], "2024-01-31T10:30:15.654000")
        self.assertEqual(doc["metadata"]["created_at"], "2024-01-10T08:00:00.000000")
        self.assertEqual(doc["metadata"]["updated_at"], "2024-01-31T10:30:15.654000")
        self.assertTrue(doc["is_public"])

        # sem updated, usa created
        self.assertEqual(documents[1]["origin_date"], "2024-01-10")
        self.assertEqual(documents[1]["updated"], "2024-01-10T08:00:00.000000")

    def test_is_public(self):
        documents, _ = self.harvest(
            [{"pages": 1, "documents": [
                self.make_item("aid1", is_public=False),
                # v1: status
                {k: v for k, v in self.make_item("aid2", status=True).items()
                 if k != "is_public"},
            ]}]
        )
        self.assertEqual([d["is_public"] for d in documents], [False, True])

    def test_invalid_date_is_ignored(self):
        documents, _ = self.harvest(
            [{"pages": 1, "documents": [
                self.make_item("aid1", created=None, updated="invalid")
            ]}]
        )
        self.assertIsNone(documents[0]["origin_date"])
        self.assertIsNone(documents[0]["updated"])

    def test_from_harvest_source_date_is_full_updated_date(self):
        builder = make_builder(collection_acron_list=["scl"])
        documents, _ = self.harvest(
            [{"pages": 1, "documents": [self.make_item("aid1")]}]
        )
        with patch(f"{MODULE_PATH}.Collection") as MockCollection:
            MockCollection.objects.count.return_value = 5

            fake_harvester = MagicMock()
            fake_harvester.harvest_documents.return_value = documents
            with patch.object(
                builder, "_build_harvesters", return_value=[fake_harvester]
            ):
                result = list(builder.from_harvest())

        self.assertEqual(result[0]["source_date"], "2024-01-31T10:30:15.654000")


if __name__ == "__main__":
    unittest.main()
