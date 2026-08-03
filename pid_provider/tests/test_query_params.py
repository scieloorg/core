"""
Testes para QueryBuilderPidProviderXML e as funções de comparação
(compare, compare_lists, compare_items, get_score, zero_to_none).

Atualizado para cobrir a correção do falso-match na branch journal-article:
- QueryBuilderPidProviderXML agora também lê
  `xml_adapter.xml_with_pre.body_fragment_fingerprint` (fingerprint parcial do body do artigo)
   e também `xml_adapter.xml_with_pre.body_fingerprint` (fingerprint corpo INTEIRO do artigo) 
   diretamente do xml_with_pre.
- `article_data_query` não usa mais z_partial_body isolado: delega ao
  novo `partial_body_query`, que monta `z_partial_body__in=[...]` com os
  hashes disponíveis (legado + novo fingerprint) ou, quando nenhum dos
  dois existe no XML de entrada, `z_partial_body__isnull=True` — nunca
  `z_partial_body__in=(None, None)`, que em SQL jamais casaria com
  candidatos NULL (NULL = NULL é UNKNOWN, não True).

ATENÇÃO: ajuste o caminho de import abaixo (`pid_provider.query_params`)
para o módulo real onde essas classes/funções estão definidas no projeto,
caso seja diferente.
"""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.db.models import Q

from pid_provider import exceptions
from pid_provider.query_params import (
    QueryBuilderPidProviderXML,
    compare,
    compare_items,
    compare_lists,
    get_score,
    zero_to_none,
)


def make_xml_adapter(
    data=None,
    v3=None,
    v2=None,
    aop_pid=None,
    pkg_name=None,
    sps_pkg_name=None,
    deprecated_sps_pkg_name_list=None,
    order=None,
    article_titles=None,
    surnames=None,
    collab=None,
    links=None,
    partial_body=None,
    body_fingerprint=None,
    body_fragment_fingerprint=None,
):
    """
    Monta um mock de xml_adapter com a forma esperada por
    QueryBuilderPidProviderXML.

    body_fragment_fingerprint: valor de
    xml_adapter.xml_with_pre.body_fragment_fingerprint, o novo sinal
    (hash do corpo inteiro do artigo) usado em partial_body_query.
    """
    adapter = MagicMock()
    adapter.data = data or {}
    adapter.get_data_to_compare.return_value = {}
    adapter.v3 = v3
    adapter.v2 = v2
    adapter.aop_pid = aop_pid
    adapter.pkg_name = pkg_name
    adapter.sps_pkg_name = sps_pkg_name
    adapter.order = order
    adapter.xml_with_pre.deprecated_sps_pkg_name_list = deprecated_sps_pkg_name_list or []
    adapter.xml_with_pre.body_fingerprint = body_fingerprint
    adapter.xml_with_pre.body_fragment_fingerprint = body_fragment_fingerprint
    adapter.xml_with_pre.get_article_data.return_value = {
        "article_titles": article_titles or [],
        "surnames": surnames,
        "collab": collab,
        "links": links,
        "partial_body": partial_body,
    }
    return adapter


class ValidateInputDataTests(SimpleTestCase):

    def test_raises_when_pub_year_missing(self):
        adapter = make_xml_adapter(data={})
        qbuilder = QueryBuilderPidProviderXML(adapter)
        with self.assertRaises(
            exceptions.RequiredPublicationYearErrorToGetPidProviderXMLError
        ):
            qbuilder.validate_input_data()

    def test_raises_when_issn_missing(self):
        adapter = make_xml_adapter(data={"pub_year": "2026"})
        qbuilder = QueryBuilderPidProviderXML(adapter)
        with self.assertRaises(exceptions.RequiredISSNErrorToGetPidProviderXMLError):
            qbuilder.validate_input_data()

    def test_passes_when_location_params_present(self):
        """Se houver dado de localização do artigo, retorna sem checar dados textuais."""
        adapter = make_xml_adapter(
            data={
                "pub_year": "2026",
                "issn_print": "1234-5678",
                "fpage": "10",
            },
            article_titles=[],
            surnames=None,
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        qbuilder.validate_input_data()  # não deve levantar

    def test_passes_when_textual_data_present(self):
        adapter = make_xml_adapter(
            data={"pub_year": "2026", "issn_electronic": "0000-1111"},
            article_titles=["Título do artigo"],
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        qbuilder.validate_input_data()  # não deve levantar

    def test_passes_when_only_surnames_present(self):
        adapter = make_xml_adapter(
            data={"pub_year": "2026", "issn_electronic": "0000-1111"},
            surnames="Silva",
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        qbuilder.validate_input_data()  # não deve levantar

    def test_raises_not_enough_parameters_when_all_empty(self):
        adapter = make_xml_adapter(
            data={"pub_year": "2026", "issn_electronic": "0000-1111"},
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        with self.assertRaises(exceptions.NotEnoughParametersToGetPidProviderXMLError):
            qbuilder.validate_input_data()

    def test_raises_not_enough_parameters_when_titles_are_blank(self):
        """Lista de títulos só com valores falsy deve ser tratada como vazia."""
        adapter = make_xml_adapter(
            data={"pub_year": "2026", "issn_electronic": "0000-1111"},
            article_titles=["", None],
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        with self.assertRaises(exceptions.NotEnoughParametersToGetPidProviderXMLError):
            qbuilder.validate_input_data()


class PkgNameListTests(SimpleTestCase):

    def test_combines_all_sources_and_drops_falsy(self):
        adapter = make_xml_adapter(
            data={},
            pkg_name="pkg-a",
            sps_pkg_name="pkg-b",
            deprecated_sps_pkg_name_list=["pkg-c", "", None, "pkg-a"],
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        self.assertEqual(qbuilder.pkg_name_list, {"pkg-a", "pkg-b", "pkg-c"})

    def test_empty_when_no_names_available(self):
        adapter = make_xml_adapter(data={}, pkg_name=None, sps_pkg_name=None)
        qbuilder = QueryBuilderPidProviderXML(adapter)
        self.assertEqual(qbuilder.pkg_name_list, set())


class IdentifierQueriesTests(SimpleTestCase):

    def test_empty_when_nothing_set(self):
        adapter = make_xml_adapter(data={})
        qbuilder = QueryBuilderPidProviderXML(adapter)
        self.assertEqual(qbuilder.identifier_queries, Q())

    def test_v3_only(self):
        adapter = make_xml_adapter(data={}, v3="V3-123")
        qbuilder = QueryBuilderPidProviderXML(adapter)
        self.assertEqual(qbuilder.identifier_queries, Q(v3="V3-123"))

    def test_v2_and_aop_pid_combine_with_or(self):
        adapter = make_xml_adapter(data={}, v2="V2-1", aop_pid="AOP-1")
        qbuilder = QueryBuilderPidProviderXML(adapter)
        expected = Q(v2="V2-1") | (Q(v2="AOP-1") | Q(aop_pid="AOP-1"))
        self.assertEqual(qbuilder.identifier_queries, expected)

    def test_includes_pkg_names_and_main_doi(self):
        adapter = make_xml_adapter(
            data={"main_doi": "10.1234/xyz"},
            pkg_name="pkg-a",
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        expected = Q(pkg_name__in={"pkg-a"}) | Q(main_doi="10.1234/xyz")
        self.assertEqual(qbuilder.identifier_queries, expected)


class IssnQueryTests(SimpleTestCase):

    def test_raises_when_no_issn(self):
        adapter = make_xml_adapter(data={})
        qbuilder = QueryBuilderPidProviderXML(adapter)
        with self.assertRaises(exceptions.RequiredISSNErrorToGetPidProviderXMLError):
            qbuilder.issn_query

    def test_electronic_only(self):
        adapter = make_xml_adapter(data={"issn_electronic": "0000-1111"})
        qbuilder = QueryBuilderPidProviderXML(adapter)
        self.assertEqual(qbuilder.issn_query, Q(issn_electronic="0000-1111"))

    def test_print_only(self):
        adapter = make_xml_adapter(data={"issn_print": "1234-5678"})
        qbuilder = QueryBuilderPidProviderXML(adapter)
        self.assertEqual(qbuilder.issn_query, Q(issn_print="1234-5678"))

    def test_both_issn_combine_with_or(self):
        adapter = make_xml_adapter(
            data={"issn_electronic": "0000-1111", "issn_print": "1234-5678"}
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        expected = Q(issn_electronic="0000-1111") | Q(issn_print="1234-5678")
        self.assertEqual(qbuilder.issn_query, expected)


class IssueParamsTests(SimpleTestCase):

    def test_returns_expected_keys(self):
        adapter = make_xml_adapter(
            data={"pub_year": "2026", "volume": "10", "number": "2", "suppl": "1"}
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        self.assertEqual(
            qbuilder.issue_params,
            {"pub_year": "2026", "volume": "10", "number": "2", "suppl": "1"},
        )

    def test_missing_values_are_none(self):
        adapter = make_xml_adapter(data={})
        qbuilder = QueryBuilderPidProviderXML(adapter)
        self.assertEqual(
            qbuilder.issue_params,
            {"pub_year": None, "volume": None, "number": None, "suppl": None},
        )


class ArticleLocationParamsTests(SimpleTestCase):

    def test_without_order(self):
        adapter = make_xml_adapter(
            data={"elocation_id": "e123", "fpage": "10", "lpage": "20"},
            order=None,
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        params = qbuilder.article_location_params
        self.assertEqual(
            params,
            {
                "elocation_id": "e123",
                "fpage": "10",
                "fpage_seq": None,
                "lpage": "20",
            },
        )
        self.assertNotIn("v2__endswith", params)

    def test_with_order_adds_v2_endswith(self):
        adapter = make_xml_adapter(data={}, order="00003")
        qbuilder = QueryBuilderPidProviderXML(adapter)
        params = qbuilder.article_location_params
        self.assertEqual(params["v2__endswith"], "00003")


class PartialBodyQueryTests(SimpleTestCase):
    """
    Cobre especificamente o fix do incidente: z_partial_body agora aceita
    dois formatos de hash (legado e fingerprint do corpo inteiro), e o
    caso "nenhum dos dois presente" precisa cair em isnull=True, nunca em
    __in=(None, None).
    """

    def test_uses_in_with_only_legacy_partial_body(self):
        adapter = make_xml_adapter(
            data={"z_partial_body": "hash-legado"},
            body_fragment_fingerprint=None,
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        self.assertEqual(
            qbuilder.partial_body_query, Q(z_partial_body__in=["hash-legado"])
        )

    def test_uses_in_with_only_body_fragment_fingerprint(self):
        adapter = make_xml_adapter(
            data={},
            body_fragment_fingerprint="hash-fragmento-do-corpo",
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        self.assertEqual(
            qbuilder.partial_body_query,
            Q(z_partial_body__in=["hash-fragmento-do-corpo"]),
        )

    def test_uses_in_with_both_hashes_when_both_present_and_different(self):
        adapter = make_xml_adapter(
            data={"z_partial_body": "hash-legado"},
            body_fragment_fingerprint="hash-fragmento-do-corpo",
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        self.assertEqual(
            qbuilder.partial_body_query,
            Q(z_partial_body__in={"hash-legado", "hash-fragmento-do-corpo"}),
        )

    def test_deduplicates_when_both_hashes_are_equal(self):
        adapter = make_xml_adapter(
            data={"z_partial_body": "hash-igual"},
            body_fragment_fingerprint="hash-igual",
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        self.assertEqual(
            qbuilder.partial_body_query, Q(z_partial_body__in=["hash-igual"])
        )

    def test_uses_isnull_when_neither_hash_is_present(self):
        """
        Regressão do incidente: quando o XML de entrada não tem nenhum
        hash de corpo, a query deve usar isnull=True (equivalente ao
        antigo Q(z_partial_body=None)), e JAMAIS __in=(None, None), que
        em SQL nunca casaria com candidatos cujo z_partial_body é NULL
        (NULL = NULL é UNKNOWN, não True).
        """
        adapter = make_xml_adapter(data={}, body_fragment_fingerprint=None)
        qbuilder = QueryBuilderPidProviderXML(adapter)
        self.assertEqual(qbuilder.partial_body_query, Q(z_partial_body__isnull=True))
        self.assertNotEqual(
            qbuilder.partial_body_query, Q(z_partial_body__in=(None, None))
        )

    def test_combines_textual_fields_with_all_three_body_hashes(self):
        """
        article_data_query propaga corretamente o candidato adicional
        body_fingerprint (corpo inteiro) através de partial_body_query,
        junto com z_partial_body legado e body_fragment_fingerprint.
        """
        adapter = make_xml_adapter(
            data={
                "z_surnames": "Silva",
                "z_collab": None,
                "z_links": None,
                "z_partial_body": "hash-legado",
            },
            body_fragment_fingerprint="hash-fragmento-do-corpo",
            body_fingerprint="hash-corpo-inteiro",
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        expected = Q(z_surnames="Silva", z_collab=None, z_links=None) & Q(
            z_partial_body__in={
                "hash-legado",
                "hash-fragmento-do-corpo",
                "hash-corpo-inteiro",
            }
        )
        self.assertEqual(qbuilder.article_data_query, expected)

    def test_two_articles_with_same_legacy_hash_but_different_body_fingerprint_differ(self):
        """
        Regressão direta do incidente original: dois artigos com o mesmo
        rótulo genérico em z_partial_body legado (ex. "ARTIGO DE REVISÃO")
        mas com body_fingerprint (corpo inteiro) diferentes devem produzir
        queries distintas — o falso-positivo de match não deve mais ocorrer.
        """
        adapter_a = make_xml_adapter(
            data={"z_partial_body": "rotulo-generico-artigo-revisao"},
            body_fragment_fingerprint=None,
            body_fingerprint="hash-corpo-artigo-a",
        )
        adapter_b = make_xml_adapter(
            data={"z_partial_body": "rotulo-generico-artigo-revisao"},
            body_fragment_fingerprint=None,
            body_fingerprint="hash-corpo-artigo-b",
        )
        qbuilder_a = QueryBuilderPidProviderXML(adapter_a)
        qbuilder_b = QueryBuilderPidProviderXML(adapter_b)
        self.assertNotEqual(
            qbuilder_a.article_data_query, qbuilder_b.article_data_query
        )


class ArticleDataQueryTests(SimpleTestCase):
    """
    article_data_query agora delega o campo z_partial_body inteiramente a
    partial_body_query (ver PartialBodyQueryTests) e mantém AND puro para
    z_surnames/z_collab/z_links.
    """

    def test_combines_textual_fields_with_partial_body_query_both_hashes(self):
        adapter = make_xml_adapter(
            data={
                "z_surnames": "Silva",
                "z_collab": None,
                "z_links": None,
                "z_partial_body": "hash-legado",
            },
            body_fragment_fingerprint="hash-fragmento-do-corpo",
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        expected = Q(z_surnames="Silva", z_collab=None, z_links=None) & Q(
            z_partial_body__in={"hash-legado", "hash-fragmento-do-corpo"}
        )
        self.assertEqual(qbuilder.article_data_query, expected)

    def test_falls_back_to_isnull_when_no_body_hash_available(self):
        adapter = make_xml_adapter(data={}, body_fragment_fingerprint=None)
        qbuilder = QueryBuilderPidProviderXML(adapter)
        expected = Q(z_surnames=None, z_collab=None, z_links=None) & Q(
            z_partial_body__isnull=True
        )
        self.assertEqual(qbuilder.article_data_query, expected)

    def test_two_different_articles_produce_different_queries(self):
        """
        Regressão conceitual do incidente: dois artigos com hashes de
        corpo diferentes (mesmo que ambos tenham, no passado, colidido
        via z_partial_body legado genérico) agora produzem queries IN
        distintas, pois o fingerprint do corpo inteiro entra na
        composição.
        """
        adapter_a = make_xml_adapter(
            data={"z_partial_body": "rotulo-generico-artigo-revisao"},
            body_fragment_fingerprint="hash-corpo-artigo-a",
        )
        adapter_b = make_xml_adapter(
            data={"z_partial_body": "rotulo-generico-artigo-revisao"},
            body_fragment_fingerprint="hash-corpo-artigo-b",
        )
        qbuilder_a = QueryBuilderPidProviderXML(adapter_a)
        qbuilder_b = QueryBuilderPidProviderXML(adapter_b)
        self.assertNotEqual(
            qbuilder_a.article_data_query, qbuilder_b.article_data_query
        )


class GetArticleDataQueryTests(SimpleTestCase):
    """Método usado em select_records (models.py)."""

    def test_issue_true_combines_article_data_issue_and_location_params(self):
        adapter = make_xml_adapter(
            data={
                "z_surnames": "Silva",
                "pub_year": "2026",
                "volume": "10",
                "number": "2",
                "suppl": None,
                "elocation_id": "e1",
                "fpage": "10",
                "lpage": "20",
            },
            body_fragment_fingerprint=None,
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        result = qbuilder.get_article_data_query(issue=True)
        expected = (
            qbuilder.article_data_query
            & Q(**qbuilder.issue_params)
            & Q(**qbuilder.article_location_params)
        )
        self.assertEqual(result, expected)

    def test_issue_false_requires_issue_and_location_fields_null(self):
        adapter = make_xml_adapter(
            data={"z_surnames": "Silva"}, body_fragment_fingerprint=None
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        result = qbuilder.get_article_data_query(issue=False)
        expected = qbuilder.article_data_query & Q(
            volume__isnull=True,
            number__isnull=True,
            suppl__isnull=True,
            elocation_id__isnull=True,
            fpage__isnull=True,
            lpage__isnull=True,
        )
        self.assertEqual(result, expected)

    def test_issue_true_and_false_produce_different_queries(self):
        adapter = make_xml_adapter(
            data={"z_surnames": "Silva", "pub_year": "2026"},
            body_fragment_fingerprint=None,
        )
        qbuilder = QueryBuilderPidProviderXML(adapter)
        self.assertNotEqual(
            qbuilder.get_article_data_query(issue=True),
            qbuilder.get_article_data_query(issue=False),
        )


class ZeroToNoneTests(SimpleTestCase):

    def test_returns_none_for_falsy_input(self):
        self.assertIsNone(zero_to_none(None))
        self.assertIsNone(zero_to_none(""))

    def test_returns_none_when_digit_zero(self):
        self.assertIsNone(zero_to_none("0"))

    def test_returns_data_when_non_digit(self):
        self.assertEqual(zero_to_none("abc"), "abc")

    def test_returns_data_when_digit_nonzero(self):
        self.assertEqual(zero_to_none("5"), "5")


class GetScoreTests(SimpleTestCase):

    def test_equal_and_truthy_returns_max(self):
        self.assertEqual(get_score("a", "a", min_value=0, max_value=10), 10)

    def test_equal_and_falsy_returns_min(self):
        self.assertEqual(get_score(None, None, min_value=1, max_value=10), 1)

    def test_different_returns_zero(self):
        self.assertEqual(get_score("a", "b", min_value=0, max_value=10), 0)


class CompareListsTests(SimpleTestCase):

    def test_identical_lists_return_one(self):
        self.assertEqual(compare_lists(["a", "b"], ["a", "b"]), 1)

    def test_empty_xml_adapter_titles_returns_zero(self):
        self.assertEqual(compare_lists(["a"], []), 0)

    def test_empty_registered_returns_zero(self):
        self.assertEqual(compare_lists([], ["a"]), 0)

    @patch("pid_provider.query_params.how_similar")
    def test_delegates_to_how_similar_when_different(self, mock_how_similar):
        mock_how_similar.return_value = 0.75
        result = compare_lists(["Título Um"], ["Titulo Dois"])
        self.assertEqual(result, 0.75)
        mock_how_similar.assert_called_once()


class CompareItemsTests(SimpleTestCase):

    def test_list_field_uses_compare_lists(self):
        result = compare_items("titles", ["a", "b"], ["a", "b"])
        self.assertEqual(result, {"label": "titles", "score": 1})

    def test_equal_scalars_score_one_without_registered_key(self):
        result = compare_items("z_surnames", "Silva", "Silva")
        self.assertEqual(result, {"label": "z_surnames", "score": 1})

    def test_none_and_falsy_are_treated_as_equal(self):
        result = compare_items("z_collab", None, "")
        self.assertEqual(result, {"label": "z_collab", "score": 1})

    @patch("pid_provider.query_params.how_similar")
    def test_different_scalars_uses_how_similar_and_includes_registered(
        self, mock_how_similar
    ):
        mock_how_similar.return_value = 0.4
        result = compare_items("z_surnames", "Silva", "Souza")
        self.assertEqual(
            result, {"label": "z_surnames", "score": 0.4, "registered": "Silva"}
        )
        mock_how_similar.assert_called_once_with("Souza", "Silva")

    @patch("pid_provider.query_params.how_similar")
    def test_none_input_data_falls_back_to_empty_string_for_how_similar(
        self, mock_how_similar
    ):
        mock_how_similar.return_value = 0.2
        result = compare_items("z_links", "algum-link", None)
        self.assertEqual(
            result, {"label": "z_links", "score": 0.2, "registered": "algum-link"}
        )
        mock_how_similar.assert_called_once_with("", "algum-link")

    @patch("pid_provider.query_params.how_similar")
    def test_none_registered_falls_back_to_empty_string_for_how_similar(
        self, mock_how_similar
    ):
        mock_how_similar.return_value = 0.3
        result = compare_items("z_links", None, "algum-link")
        self.assertEqual(result, {"label": "z_links", "score": 0.3, "registered": None})
        mock_how_similar.assert_called_once_with("algum-link", "")


class CompareTests(SimpleTestCase):

    @patch("pid_provider.query_params.how_similar")
    def test_aggregates_scores_from_all_items(self, mock_how_similar):
        mock_how_similar.return_value = 0.5
        registered_items = {"title": "Título A", "z_surnames": "Silva"}
        input_data = {"title": "Título A", "z_surnames": "Souza"}

        result = compare(registered_items, input_data)

        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(result["total_score"], 1.5)  # 1 (match) + 0.5 (mocked)
        self.assertEqual(result["percentual_score"], 0.75)

    def test_missing_input_key_is_treated_as_none(self):
        registered_items = {"z_collab": None}
        input_data = {}

        result = compare(registered_items, input_data)

        self.assertEqual(result["total_score"], 1)
        self.assertEqual(result["percentual_score"], 1)