from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.test import TestCase

from pid_provider.models import PidProviderXML


User = get_user_model()


def build_get_article_data_query_side_effect(issue_true_query, issue_false_query):
    """
    Constrói o side_effect para `qbuilder.get_article_data_query(issue)`,
    já que agora é ele quem decide a query final (antes, select_records
    montava `Q(**issue_params) & article_data_query` diretamente).
    """
    def _side_effect(issue):
        return issue_true_query if issue else issue_false_query
    return _side_effect


class PidProviderXMLSelectRecordsTests(TestCase):
    """
    select_records agora é um generator: apenas yield-a tuplas
    (label, lista_de_candidatos_materializada) com os candidatos de
    cada estratégia de busca. Cada branch é convertida com list(...)
    dentro do próprio método (ver docstring de select_records), então
    o que chega aqui NÃO é mais um QuerySet — é uma list — e portanto
    não expõe métodos como .count() ou .filter().
    Ele NÃO chama mais best_matches nem levanta DoesNotExist —
    essa orquestração ficou fora deste método.

    IMPORTANTE (pós-diff): as branches 2 e 3 não usam mais
    `qbuilder.issue_params` e `qbuilder.article_data_query` diretamente —
    passaram a usar `qbuilder.get_article_data_query(issue=True)` (branch
    "journal-issue-article") e `qbuilder.get_article_data_query(issue=False)`
    (branch "journal-article"). Por isso o mock precisa configurar
    `get_article_data_query` (não mais `issue_params`/`article_data_query`
    isolados).
    """

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")

        self.xml_adapter_mock = MagicMock()
        self.xml_adapter_mock.xml_with_pre.article_titles_texts = "Titulo de Teste"
        self.xml_adapter_mock.z_surnames = "Silva"
        self.xml_adapter_mock.z_collab = None
        self.xml_adapter_mock.z_links = None
        self.xml_adapter_mock.z_partial_body = "Corpo parcial do artigo"
        self.xml_adapter_mock.sps_pkg_name = "test_package"

    @patch("pid_provider.models.QueryBuilderPidProviderXML")
    def test_select_records_yields_three_labeled_lists_in_order(self, mock_qbuilder_cls):
        """O generator deve produzir, nesta ordem: ids, journal-issue-article, journal-article."""
        mock_qbuilder = mock_qbuilder_cls.return_value
        mock_qbuilder.identifier_queries = Q(v3="12345")
        mock_qbuilder.issn_query = Q(issn_print="1234-5678")

        # issue=True -> exige pub_year=2026 (equivalente ao antigo issue_params)
        # issue=False -> ignora pub_year, só olha z_surnames (equivalente ao
        # antigo article_data_query "puro")
        mock_qbuilder.get_article_data_query.side_effect = (
            build_get_article_data_query_side_effect(
                issue_true_query=Q(pub_year=2026) & Q(z_surnames="Silva"),
                issue_false_query=Q(z_surnames="Silva"),
            )
        )

        record_by_id = PidProviderXML.objects.create(
            creator=self.user, v3="12345", registered_in_core=True
        )
        record_by_journal_issue_article = PidProviderXML.objects.create(
            creator=self.user,
            issn_print="1234-5678",
            pub_year=2026,
            z_surnames="Silva",
        )
        record_by_journal_article_only = PidProviderXML.objects.create(
            creator=self.user,
            issn_print="1234-5678",
            pub_year=1999,
            z_surnames="Silva",
        )

        results = list(PidProviderXML.select_records(self.xml_adapter_mock))

        mock_qbuilder.validate_input_data.assert_called_once()

        self.assertEqual(len(results), 3)

        labels = [label for label, _ in results]
        self.assertEqual(labels, ["ids", "journal-issue-article", "journal-article"])

        # cada branch já vem materializada como list (não QuerySet)
        for _label, candidates in results:
            self.assertIsInstance(candidates, list)

        # get_article_data_query deve ter sido chamado com issue=True e
        # depois issue=False, nesta ordem
        calls = [c.args[0] if c.args else c.kwargs.get("issue") for c in mock_qbuilder.get_article_data_query.call_args_list]
        self.assertEqual(calls, [True, False])

        # 1) ids: só o registro com v3 correspondente
        ids_list = results[0][1]
        self.assertIn(record_by_id, ids_list)
        self.assertNotIn(record_by_journal_issue_article, ids_list)
        self.assertNotIn(record_by_journal_article_only, ids_list)

        # 2) journal + issue + artigo: só o que bate no pub_year certo
        journal_issue_article_list = results[1][1]
        self.assertIn(record_by_journal_issue_article, journal_issue_article_list)
        self.assertNotIn(record_by_journal_article_only, journal_issue_article_list)

        # 3) journal + artigo (ignora issue): pega os dois do mesmo issn/z_surnames
        journal_article_list = results[2][1]
        self.assertIn(record_by_journal_issue_article, journal_article_list)
        self.assertIn(record_by_journal_article_only, journal_article_list)

    @patch("pid_provider.models.QueryBuilderPidProviderXML")
    def test_select_records_empty_lists_when_no_match(self, mock_qbuilder_cls):
        """Sem nenhum registro correspondente, cada lista yield deve vir vazia (sem levantar exceção)."""
        mock_qbuilder = mock_qbuilder_cls.return_value
        mock_qbuilder.identifier_queries = Q(v3="nao_existe")
        mock_qbuilder.issn_query = Q(issn_print="0000-0000")
        mock_qbuilder.get_article_data_query.side_effect = (
            build_get_article_data_query_side_effect(
                issue_true_query=Q(pub_year=1900) & Q(z_surnames="Ninguem"),
                issue_false_query=Q(z_surnames="Ninguem"),
            )
        )

        results = list(PidProviderXML.select_records(self.xml_adapter_mock))

        self.assertEqual(len(results), 3)
        for _label, candidates in results:
            self.assertIsInstance(candidates, list)
            # listas usam len(), não .count() (que é método de QuerySet)
            self.assertEqual(len(candidates), 0)

    @patch("pid_provider.models.QueryBuilderPidProviderXML")
    def test_select_records_is_lazy_until_iterated(self, mock_qbuilder_cls):
        """
        Por ser generator, nada é executado na chamada da função:
        QueryBuilderPidProviderXML(...) e validate_input_data() só
        rodam quando o generator é de fato consumido (primeiro next()).
        get_article_data_query só é chamado a partir do 2º/3º next(),
        já que a 1ª branch ("ids") não depende dele.
        """
        mock_qbuilder = mock_qbuilder_cls.return_value
        mock_qbuilder.identifier_queries = Q(v3="qualquer")
        mock_qbuilder.issn_query = Q(issn_print="0000-0000")
        mock_qbuilder.get_article_data_query.side_effect = (
            build_get_article_data_query_side_effect(
                issue_true_query=Q(),
                issue_false_query=Q(),
            )
        )

        gen = PidProviderXML.select_records(self.xml_adapter_mock)

        # nada foi executado ainda
        mock_qbuilder_cls.assert_not_called()
        mock_qbuilder.validate_input_data.assert_not_called()

        next(gen)  # yield "ids"

        mock_qbuilder_cls.assert_called_once_with(self.xml_adapter_mock)
        mock_qbuilder.validate_input_data.assert_called_once()
        # "ids" não usa get_article_data_query
        mock_qbuilder.get_article_data_query.assert_not_called()

        next(gen)  # yield "journal-issue-article"
        mock_qbuilder.get_article_data_query.assert_called_once_with(issue=True)

        next(gen)  # yield "journal-article"
        self.assertEqual(mock_qbuilder.get_article_data_query.call_count, 2)
        mock_qbuilder.get_article_data_query.assert_called_with(issue=False)