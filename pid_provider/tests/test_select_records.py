from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.test import TestCase

from pid_provider.models import PidProviderXML


User = get_user_model()


def build_get_article_data_query_side_effect(queries):
    """
    Constrói o side_effect para `qbuilder.get_article_data_query(issue,
    flexible)`. `queries` é um dict {(issue, flexible): Q}.
    """
    def _side_effect(issue, flexible):
        return queries[(issue, flexible)]
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

    IMPORTANTE (pós-diff): a antiga branch única "journal-issue-article"
    (OR das 4 combinações de issue x flexible + .distinct()) foi
    dividida em duas branches sequenciais, na mesma lógica "para na
    primeira que resolver" do resto do generator:
    - "journal-issue-article-strict": OR de (issue=True, flexible=False)
      e (issue=False, flexible=False) -- exige os hashes textuais.
    - "journal-issue-article-flexible": OR de (issue=True, flexible=True)
      e (issue=False, flexible=True) -- dispensa os hashes textuais, só
      é avaliada se a branch strict não resolver (é um generator lazy).
    Nenhuma das duas usa mais .distinct(): get_article_data_query só
    filtra campos do próprio PidProviderXML (sem join), então OR nunca
    duplica linha.

    IMPORTANTE (pós-diff 2): a branch "journal-issue" (fallback que
    casava só por issue_params, ignorando conteúdo/localização) foi
    removida — considerada excessivamente permissiva (poderia trazer
    todos os artigos de um mesmo fascículo como candidatos).

    IMPORTANTE (pós-diff 3): a branch "pkg_name" foi removida de
    select_records — pkg_name deixou de ser usado como critério de
    busca de candidatos (ver QueryBuilderPidProviderXML.pkg_name_queries,
    que continua existindo/testada isoladamente, mas não é mais
    consumida aqui).
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
        """O generator deve produzir, nesta ordem: ids, strict, flexible."""
        mock_qbuilder = mock_qbuilder_cls.return_value
        mock_qbuilder.identifier_queries = Q(v3="12345")
        mock_qbuilder.issn_query = Q(issn_print="1234-5678")

        mock_qbuilder.get_article_data_query.side_effect = (
            build_get_article_data_query_side_effect({
                (True, False): Q(volume="strict-issue"),
                (False, False): Q(volume="strict-noissue"),
                (True, True): Q(volume="flexible-issue"),
                (False, True): Q(volume="flexible-noissue"),
            })
        )

        record_by_id = PidProviderXML.objects.create(
            creator=self.user, v3="12345", registered_in_core=True
        )
        record_strict_issue = PidProviderXML.objects.create(
            creator=self.user, issn_print="1234-5678", volume="strict-issue",
        )
        record_strict_noissue = PidProviderXML.objects.create(
            creator=self.user, issn_print="1234-5678", volume="strict-noissue",
        )
        record_flexible_only = PidProviderXML.objects.create(
            creator=self.user, issn_print="1234-5678", volume="flexible-issue",
        )

        results = list(PidProviderXML.select_records(self.xml_adapter_mock))

        mock_qbuilder.validate_input_data.assert_called_once()

        self.assertEqual(len(results), 3)

        labels = [label for label, _ in results]
        self.assertEqual(
            labels,
            ["ids", "journal-issue-article-strict", "journal-issue-article-flexible"],
        )

        for _label, candidates in results:
            self.assertIsInstance(candidates, list)

        # 1) ids: só o registro com v3 correspondente
        self.assertEqual(results[0][1], [record_by_id])

        # 2) strict: os 2 candidatos das combinações flexible=False
        strict_list = results[1][1]
        self.assertEqual(len(strict_list), 2)
        self.assertIn(record_strict_issue, strict_list)
        self.assertIn(record_strict_noissue, strict_list)
        self.assertNotIn(record_flexible_only, strict_list)

        # 3) flexible: o candidato que só casa quando os hashes textuais
        # são dispensados
        flexible_list = results[2][1]
        self.assertIn(record_flexible_only, flexible_list)
        self.assertNotIn(record_strict_issue, flexible_list)

        # get_article_data_query foi chamado com as 4 combinações
        calls = {
            (c.kwargs.get("issue"), c.kwargs.get("flexible"))
            for c in mock_qbuilder.get_article_data_query.call_args_list
        }
        self.assertEqual(
            calls, {(True, False), (False, False), (True, True), (False, True)}
        )

    @patch("pid_provider.models.QueryBuilderPidProviderXML")
    def test_select_records_empty_lists_when_no_match(self, mock_qbuilder_cls):
        """Sem nenhum registro correspondente, cada lista yield deve vir vazia (sem levantar exceção)."""
        mock_qbuilder = mock_qbuilder_cls.return_value
        mock_qbuilder.identifier_queries = Q(v3="nao_existe")
        mock_qbuilder.issn_query = Q(issn_print="0000-0000")
        mock_qbuilder.get_article_data_query.side_effect = (
            build_get_article_data_query_side_effect({
                (True, False): Q(volume="nao_existe"),
                (False, False): Q(volume="nao_existe"),
                (True, True): Q(volume="nao_existe"),
                (False, True): Q(volume="nao_existe"),
            })
        )

        results = list(PidProviderXML.select_records(self.xml_adapter_mock))

        self.assertEqual(len(results), 3)
        for _label, candidates in results:
            self.assertIsInstance(candidates, list)
            # listas usam len(), não .count() (que é método de QuerySet)
            self.assertEqual(len(candidates), 0)

    @patch("pid_provider.models.QueryBuilderPidProviderXML")
    def test_select_records_skips_query_when_identifier_is_empty(
        self, mock_qbuilder_cls
    ):
        """
        Quando identifier_queries retorna Q() (nenhum identificador no
        XML de entrada), select_records NÃO deve filtrar com Q() vazia —
        isso casaria com TODOS os registros de PidProviderXML, e não é
        esse o comportamento esperado para "nenhum critério disponível".
        A branch "ids" deve vir vazia mesmo havendo registros na base.
        """
        mock_qbuilder = mock_qbuilder_cls.return_value
        mock_qbuilder.identifier_queries = Q()
        mock_qbuilder.issn_query = Q(issn_print="0000-0000")
        mock_qbuilder.get_article_data_query.side_effect = (
            build_get_article_data_query_side_effect({
                (True, False): Q(volume="nao_existe"),
                (False, False): Q(volume="nao_existe"),
                (True, True): Q(volume="nao_existe"),
                (False, True): Q(volume="nao_existe"),
            })
        )

        # existe pelo menos um registro na base; se "ids" filtrasse com
        # Q(), ele apareceria indevidamente nessa branch
        PidProviderXML.objects.create(creator=self.user, v3="qualquer-outro")

        results = list(PidProviderXML.select_records(self.xml_adapter_mock))

        labels = dict(results)
        self.assertEqual(labels["ids"], [])

    @patch("pid_provider.models.QueryBuilderPidProviderXML")
    def test_select_records_is_lazy_until_iterated(self, mock_qbuilder_cls):
        """
        Por ser generator, nada é executado na chamada da função:
        QueryBuilderPidProviderXML(...) e validate_input_data() só
        rodam quando o generator é de fato consumido (primeiro next()).
        A branch "ids" não usa get_article_data_query; "strict" chama-o
        2 vezes (issue=True/False, flexible=False); "flexible" só é
        avaliada (e get_article_data_query só sobe pra 4 chamadas) se o
        consumidor pedir o 3º next().
        """
        mock_qbuilder = mock_qbuilder_cls.return_value
        mock_qbuilder.identifier_queries = Q(v3="qualquer")
        mock_qbuilder.issn_query = Q(issn_print="0000-0000")
        mock_qbuilder.get_article_data_query.side_effect = (
            build_get_article_data_query_side_effect({
                (True, False): Q(),
                (False, False): Q(),
                (True, True): Q(),
                (False, True): Q(),
            })
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

        next(gen)  # yield "journal-issue-article-strict"
        self.assertEqual(mock_qbuilder.get_article_data_query.call_count, 2)
        strict_calls = {
            (c.kwargs.get("issue"), c.kwargs.get("flexible"))
            for c in mock_qbuilder.get_article_data_query.call_args_list
        }
        self.assertEqual(strict_calls, {(True, False), (False, False)})

        next(gen)  # yield "journal-issue-article-flexible"
        self.assertEqual(mock_qbuilder.get_article_data_query.call_count, 4)
