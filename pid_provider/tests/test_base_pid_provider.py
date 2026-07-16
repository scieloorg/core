"""
Testes para pid_provider.base_pid_provider.BasePidProvider

Cobre:
- provide_pid_for_xml_with_pre
- provide_pid_for_xml_zip
- provide_pid_for_xml_uri
- is_registered_xml_with_pre
- is_registered_xml_uri
- is_registered_xml_zip

Toda a camada externa (PidProviderXML, XMLURL, XMLWithPre, UnexpectedEvent)
é mockada — estes são testes unitários "puros", sem tocar banco de dados.

Como rodar (ajuste o caminho do app se necessário):
    python manage.py test pid_provider.tests.test_base_pid_provider
"""
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase

from pid_provider.base_pid_provider import BasePidProvider


def make_xml_with_pre(filename="doc.xml"):
    xwp = MagicMock()
    xwp.filename = filename
    return xwp


def make_user(username="tester"):
    user = MagicMock()
    user.username = username
    return user


# ---------------------------------------------------------------------------
# provide_pid_for_xml_with_pre
# ---------------------------------------------------------------------------
@patch("pid_provider.base_pid_provider.PidProviderXML")
class ProvidePidForXMLWithPreTest(SimpleTestCase):
    def setUp(self):
        self.provider = BasePidProvider()
        self.user = make_user()
        self.xwp = make_xml_with_pre()

    def test_calls_register_with_expected_args_default_caller(self, mock_ppx):
        mock_ppx.register.return_value = {"v3": "abc", "xml_changed": {}}

        result = self.provider.provide_pid_for_xml_with_pre(
            self.xwp,
            "name.xml",
            self.user,
            origin_date="2024-01-01",
            force_update=False,
            is_published=True,
            origin="some/path.xml",
            registered_in_core=None,
            caller=None,
            auto_solve_pid_conflict=True,
        )

        mock_ppx.register.assert_called_once_with(
            self.xwp,
            "name.xml",
            self.user,
            origin_date="2024-01-01",
            force_update=False,
            is_published=True,
            origin="some/path.xml",
            # registered_in_core=None (recebido) or self.caller=="core" (False) -> False
            registered_in_core=False,
            auto_solve_pid_conflict=True,
        )
        self.assertEqual(result["v3"], "abc")
        self.assertIs(result["xml_with_pre"], self.xwp)
        self.assertFalse(result["apply_xml_changes"])

    def test_caller_core_forces_registered_in_core_true(self, mock_ppx):
        mock_ppx.register.return_value = {"xml_changed": {"pid_v3": "novo"}}

        result = self.provider.provide_pid_for_xml_with_pre(
            self.xwp, "name.xml", self.user, caller="core"
        )

        _, kwargs = mock_ppx.register.call_args
        self.assertTrue(kwargs["registered_in_core"])
        # caller == "core" e xml_changed truthy -> apply_xml_changes True
        self.assertTrue(result["apply_xml_changes"])

    def test_registered_in_core_explicit_true_wins_even_without_core_caller(
        self, mock_ppx
    ):
        mock_ppx.register.return_value = {"xml_changed": None}

        self.provider.provide_pid_for_xml_with_pre(
            self.xwp,
            "name.xml",
            self.user,
            registered_in_core=True,
            caller="upload",
        )

        _, kwargs = mock_ppx.register.call_args
        self.assertTrue(kwargs["registered_in_core"])

    def test_apply_xml_changes_false_when_caller_not_core_even_if_changed(
        self, mock_ppx
    ):
        mock_ppx.register.return_value = {"xml_changed": {"pid_v3": "x"}}

        result = self.provider.provide_pid_for_xml_with_pre(
            self.xwp, "name.xml", self.user, caller="upload"
        )
        self.assertFalse(result["apply_xml_changes"])

    def test_apply_xml_changes_false_when_core_but_no_change(self, mock_ppx):
        mock_ppx.register.return_value = {"xml_changed": {}}

        result = self.provider.provide_pid_for_xml_with_pre(
            self.xwp, "name.xml", self.user, caller="core"
        )
        self.assertFalse(result["apply_xml_changes"])

    def test_sets_self_caller_attribute(self, mock_ppx):
        mock_ppx.register.return_value = {}
        self.provider.provide_pid_for_xml_with_pre(
            self.xwp, "name.xml", self.user, caller="core"
        )
        self.assertEqual(self.provider.caller, "core")


# ---------------------------------------------------------------------------
# provide_pid_for_xml_zip
# ---------------------------------------------------------------------------
@patch("pid_provider.base_pid_provider.UnexpectedEvent")
@patch("pid_provider.base_pid_provider.XMLWithPre")
class ProvidePidForXMLZipTest(SimpleTestCase):
    def setUp(self):
        self.provider = BasePidProvider()
        self.user = make_user()

    def test_yields_one_result_per_xml_in_zip(self, mock_xwp_cls, mock_event):
        xwp1 = make_xml_with_pre("a.xml")
        xwp2 = make_xml_with_pre("b.xml")
        mock_xwp_cls.create.return_value = [xwp1, xwp2]

        with patch.object(
            self.provider,
            "provide_pid_for_xml_with_pre",
            side_effect=[{"v3": "pid-a"}, {"v3": "pid-b"}],
        ) as mock_inner:
            results = list(
                self.provider.provide_pid_for_xml_zip(
                    "/tmp/pacote.zip",
                    self.user,
                    force_update=True,
                    caller="upload",
                    auto_solve_pid_conflict=False,
                )
            )

        mock_xwp_cls.create.assert_called_once_with(path="/tmp/pacote.zip")
        self.assertEqual(results, [{"v3": "pid-a"}, {"v3": "pid-b"}])

        # confirma os argumentos repassados para cada chamada interna
        self.assertEqual(mock_inner.call_count, 2)
        first_call_kwargs = mock_inner.call_args_list[0].kwargs
        self.assertEqual(first_call_kwargs["origin"], "/tmp/pacote.zip")
        self.assertTrue(first_call_kwargs["force_update"])
        self.assertEqual(first_call_kwargs["caller"], "upload")
        self.assertFalse(first_call_kwargs["auto_solve_pid_conflict"])

        # nome/xml_with_pre repassados posicionalmente
        args0 = mock_inner.call_args_list[0].args
        self.assertIs(args0[0], xwp1)
        self.assertEqual(args0[1], "a.xml")
        self.assertIs(args0[2], self.user)

    def test_exception_creates_unexpected_event_and_yields_error_dict(
        self, mock_xwp_cls, mock_event
    ):
        mock_xwp_cls.create.side_effect = ValueError("zip corrompido")

        results = list(
            self.provider.provide_pid_for_xml_zip("/tmp/ruim.zip", self.user)
        )

        self.assertEqual(len(results), 1)
        self.assertIn("error_msg", results[0])
        self.assertEqual(results[0]["error_type"], str(ValueError))

        mock_event.create.assert_called_once()
        _, kwargs = mock_event.create.call_args
        self.assertIsInstance(kwargs["exception"], ValueError)
        self.assertEqual(
            kwargs["detail"]["operation"],
            "PidProvider.provide_pid_for_xml_zip",
        )
        self.assertEqual(kwargs["detail"]["input"]["zip_xml_file_path"], "/tmp/ruim.zip")
        self.assertEqual(kwargs["detail"]["input"]["user"], self.user.username)

    def test_exception_midway_still_yields_previous_results(
        self, mock_xwp_cls, mock_event
    ):
        """
        Se o generator de XMLWithPre.create falhar após já produzir itens,
        os resultados já processados devem ser preservados e, em seguida,
        o dict de erro deve ser adicionado.
        """
        xwp1 = make_xml_with_pre("a.xml")

        def broken_generator(path=None):
            yield xwp1
            raise RuntimeError("falha no meio da leitura")

        mock_xwp_cls.create.side_effect = broken_generator

        with patch.object(
            self.provider,
            "provide_pid_for_xml_with_pre",
            return_value={"v3": "pid-a"},
        ):
            results = list(
                self.provider.provide_pid_for_xml_zip("/tmp/parcial.zip", self.user)
            )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], {"v3": "pid-a"})
        self.assertIn("error_msg", results[1])


# ---------------------------------------------------------------------------
# provide_pid_for_xml_uri
# ---------------------------------------------------------------------------
@patch("pid_provider.base_pid_provider.XMLURL")
@patch("pid_provider.base_pid_provider.XMLWithPre")
class ProvidePidForXMLUriTest(SimpleTestCase):
    def setUp(self):
        self.provider = BasePidProvider()
        self.user = make_user()

    def test_success_path_records_and_returns_data(self, mock_xwp_cls, mock_xmlurl):
        xwp = make_xml_with_pre("doc.xml")
        mock_xwp_cls.create.return_value = [xwp]

        fake_response = {"v3": "pid-uri-1", "created": True}
        mock_xmlurl_obj = MagicMock()
        mock_xmlurl_obj.data = {"v3": "pid-uri-1"}
        mock_xmlurl.record.return_value = mock_xmlurl_obj

        with patch.object(
            self.provider,
            "provide_pid_for_xml_with_pre",
            return_value=fake_response,
        ) as mock_inner:
            result = self.provider.provide_pid_for_xml_uri(
                "https://example.org/doc.xml",
                "doc.xml",
                self.user,
                is_published=True,
                document_item={"status": True},
            )

        mock_inner.assert_called_once()
        self.assertEqual(result, {"v3": "pid-uri-1"})

        mock_xmlurl.record.assert_called_once()
        _, kwargs = mock_xmlurl.record.call_args
        self.assertEqual(kwargs["user"], self.user)
        self.assertEqual(kwargs["url"], "https://example.org/doc.xml")
        self.assertIsNone(kwargs["exception"])
        self.assertEqual(kwargs["response"], fake_response)
        self.assertIs(kwargs["xml_with_pre"], xwp)
        self.assertTrue(kwargs["is_public"])
        self.assertEqual(kwargs["params"]["name"], "doc.xml")

    def test_failure_inside_provide_pid_for_xml_with_pre_is_recorded(
        self, mock_xwp_cls, mock_xmlurl
    ):
        xwp = make_xml_with_pre("doc2.xml")
        mock_xwp_cls.create.return_value = [xwp]

        mock_xmlurl_obj = MagicMock()
        mock_xmlurl_obj.data = {"error_type": "RuntimeError"}
        mock_xmlurl.record.return_value = mock_xmlurl_obj

        with patch.object(
            self.provider,
            "provide_pid_for_xml_with_pre",
            side_effect=RuntimeError("falha ao registrar"),
        ):
            result = self.provider.provide_pid_for_xml_uri(
                "https://example.org/doc2.xml", "doc2.xml", self.user
            )

        self.assertEqual(result, {"error_type": "RuntimeError"})

        mock_xmlurl.record.assert_called_once()
        _, kwargs = mock_xmlurl.record.call_args
        # response não chegou a ser atribuído (permanece None)
        self.assertIsNone(kwargs["response"])
        self.assertIn("traceback_msg", kwargs)
        self.assertIn("RuntimeError", kwargs["traceback_msg"])
        self.assertIs(kwargs["xml_with_pre"], xwp)

    def test_failure_obtaining_xml_is_recorded_and_returns_data(
        self, mock_xwp_cls, mock_xmlurl
    ):
        """
        Bug corrigido: agora as etapas (a) obter XML e (b) registrar o
        PidProviderXML estão dentro do MESMO try/except. Se
        XMLWithPre.create() falhar, a exceção cai no except e
        XMLURL.record é chamado normalmente (case 'a' do docstring:
        registra URL, status e detalhe do erro) — sem propagar a exceção
        para o chamador.
        """
        mock_xwp_cls.create.side_effect = ConnectionError("host indisponível")

        mock_xmlurl_obj = MagicMock()
        mock_xmlurl_obj.data = {
            "error_type": "ConnectionError",
            "error_message": "host indisponível",
        }
        mock_xmlurl.record.return_value = mock_xmlurl_obj

        result = self.provider.provide_pid_for_xml_uri(
            "https://example.org/inacessivel.xml",
            "x.xml",
            self.user,
            is_published=False,
            document_item={"status": False},
        )

        self.assertEqual(result, mock_xmlurl_obj.data)

        mock_xmlurl.record.assert_called_once()
        _, kwargs = mock_xmlurl.record.call_args
        self.assertEqual(kwargs["url"], "https://example.org/inacessivel.xml")
        # xml_with_pre nunca chegou a ser obtido -> permanece None
        self.assertIsNone(kwargs["xml_with_pre"])
        # response nunca chegou a ser atribuído -> permanece None
        self.assertIsNone(kwargs["response"])
        self.assertIn("traceback_msg", kwargs)
        self.assertIn("ConnectionError", kwargs["traceback_msg"])
        self.assertFalse(kwargs["is_public"])
        self.assertEqual(kwargs["params"]["name"], "x.xml")

    def test_exception_variable_is_recorded_with_the_actual_caught_error(
        self, mock_xwp_cls, mock_xmlurl
    ):
        """
        Corrigido: `except Exception as exception:` agora faz o binding real
        da exceção capturada (antes o nome interno divergia e `exception`
        chegava sempre como None em XMLURL.record). A partir desta correção,
        quem falhar dentro do try (seja na obtenção do XML, seja no registro
        do PidProviderXML) deve repassar a exceção de fato capturada.
        """
        error = ValueError("qualquer erro")
        mock_xwp_cls.create.side_effect = error
        mock_xmlurl.record.return_value = MagicMock(data={})

        self.provider.provide_pid_for_xml_uri(
            "https://example.org/qualquer.xml", "x.xml", self.user
        )

        _, kwargs = mock_xmlurl.record.call_args
        self.assertIs(kwargs["exception"], error)
        self.assertIsInstance(kwargs["exception"], ValueError)


# ---------------------------------------------------------------------------
# is_registered_xml_with_pre
# ---------------------------------------------------------------------------
@patch("pid_provider.base_pid_provider.PidProviderXML")
class IsRegisteredXMLWithPreTest(SimpleTestCase):
    def test_delegates_to_pid_provider_xml(self, mock_ppx):
        xwp = make_xml_with_pre()
        mock_ppx.is_registered.return_value = {"registered": True, "v3": "abc"}

        result = BasePidProvider.is_registered_xml_with_pre(xwp, "origin.xml")

        mock_ppx.is_registered.assert_called_once_with(xwp)
        self.assertEqual(result, {"registered": True, "v3": "abc"})


# ---------------------------------------------------------------------------
# is_registered_xml_uri
# ---------------------------------------------------------------------------
@patch("pid_provider.base_pid_provider.UnexpectedEvent")
@patch("pid_provider.base_pid_provider.XMLWithPre")
class IsRegisteredXMLUriTest(SimpleTestCase):
    def test_returns_result_for_first_xml_found(self, mock_xwp_cls, mock_event):
        xwp = make_xml_with_pre()
        mock_xwp_cls.create.return_value = [xwp]

        with patch.object(
            BasePidProvider,
            "is_registered_xml_with_pre",
            return_value={"registered": True},
        ) as mock_inner:
            result = BasePidProvider.is_registered_xml_uri("https://example.org/x.xml")

        mock_xwp_cls.create.assert_called_once_with(uri="https://example.org/x.xml")
        mock_inner.assert_called_once_with(xwp, "https://example.org/x.xml")
        self.assertEqual(result, {"registered": True})

    def test_returns_error_dict_when_no_xml_found(self, mock_xwp_cls, mock_event):
        """
        Bug corrigido: antes, quando XMLWithPre.create() não produzia
        nenhum item, o `for` não executava e a função retornava None
        implicitamente. Agora há um `return` explícito com um dict de
        erro no mesmo formato usado no `except`, então o chamador nunca
        recebe None silenciosamente.
        """
        mock_xwp_cls.create.return_value = []

        result = BasePidProvider.is_registered_xml_uri("https://example.org/vazio.xml")

        self.assertIsNotNone(result)
        self.assertIn("error_msg", result)
        self.assertEqual(result["error_type"], "EmptyXMLWithPreError")
        self.assertIn("https://example.org/vazio.xml", result["error_msg"])
        # esse caminho não passa pelo except, então não deve criar UnexpectedEvent
        mock_event.create.assert_not_called()

    def test_exception_creates_unexpected_event_and_returns_error_dict(
        self, mock_xwp_cls, mock_event
    ):
        mock_xwp_cls.create.side_effect = ValueError("uri invalida")

        result = BasePidProvider.is_registered_xml_uri("https://example.org/erro.xml")

        self.assertIn("error_msg", result)
        self.assertEqual(result["error_type"], str(ValueError))
        mock_event.create.assert_called_once()
        _, kwargs = mock_event.create.call_args
        self.assertEqual(
            kwargs["detail"]["operation"], "PidProvider.is_registered_xml_uri"
        )
        self.assertEqual(
            kwargs["detail"]["input"]["xml_uri"], "https://example.org/erro.xml"
        )


# ---------------------------------------------------------------------------
# is_registered_xml_zip
# ---------------------------------------------------------------------------
@patch("pid_provider.base_pid_provider.UnexpectedEvent")
@patch("pid_provider.base_pid_provider.XMLWithPre")
class IsRegisteredXMLZipTest(SimpleTestCase):
    def test_yields_one_result_per_xml_in_zip(self, mock_xwp_cls, mock_event):
        xwp1 = make_xml_with_pre("a.xml")
        xwp2 = make_xml_with_pre("b.xml")
        mock_xwp_cls.create.return_value = [xwp1, xwp2]

        with patch.object(
            BasePidProvider,
            "is_registered_xml_with_pre",
            side_effect=[{"registered": True}, {"registered": False}],
        ) as mock_inner:
            results = list(
                BasePidProvider.is_registered_xml_zip("/tmp/pacote.zip")
            )

        mock_xwp_cls.create.assert_called_once_with(path="/tmp/pacote.zip")
        self.assertEqual(
            results, [{"registered": True}, {"registered": False}]
        )
        mock_inner.assert_has_calls(
            [call(xwp1, "/tmp/pacote.zip"), call(xwp2, "/tmp/pacote.zip")]
        )

    def test_exception_creates_unexpected_event_and_yields_error_dict(
        self, mock_xwp_cls, mock_event
    ):
        """
        Bug corrigido: dentro do generator, o bloco `except` agora faz
        `yield {...}` em vez de `return {...}` — o dict de erro chega
        ao chamador via list(...)/for, no mesmo padrão já usado em
        provide_pid_for_xml_zip.
        """
        mock_xwp_cls.create.side_effect = OSError("zip inacessível")

        results = list(BasePidProvider.is_registered_xml_zip("/tmp/ruim.zip"))

        self.assertEqual(len(results), 1)
        self.assertIn("error_msg", results[0])
        self.assertEqual(results[0]["error_type"], str(OSError))
        self.assertIn("/tmp/ruim.zip", results[0]["error_msg"])

        mock_event.create.assert_called_once()
        _, kwargs = mock_event.create.call_args
        self.assertEqual(
            kwargs["detail"]["operation"], "PidProvider.is_registered_xml_zip"
        )
