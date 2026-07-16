"""
Testes para pid_provider.models.XMLURL

Cobre:
- get() / create() / create_or_update()
- save_file()
- record() (todos os ramos: falha ao obter XML, erro inesperado, sucesso)
- data (property)
- get_status() (staticmethod)

Como rodar (ajuste o caminho do app se necessário):
    python manage.py test pid_provider.tests.test_xmlurl
"""
import zipfile
import io
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from pid_provider import choices
from pid_provider.models import XMLURL

User = get_user_model()


def make_xml_with_pre(pkg_name="pkg-01", xml_str="<article/>"):
    """Cria um mock mínimo de XMLWithPre usado por save_file/record."""
    mock = MagicMock()
    mock.sps_pkg_name = pkg_name
    mock.tostring.return_value = xml_str
    return mock


class XMLURLGetCreateTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="x")

    def test_get_without_url_raises_value_error(self):
        with self.assertRaises(ValueError):
            XMLURL.get(url=None)

    def test_get_raises_does_not_exist_when_not_found(self):
        with self.assertRaises(XMLURL.DoesNotExist):
            XMLURL.get(url="https://example.org/not-registered.xml")

    def test_create_basic(self):
        obj = XMLURL.create(
            user=self.user,
            url="https://example.org/a.xml",
            status=choices.XMLURL_STATUS_SUCCESS,
            pid="pid-v3-0001",
            detail={"foo": "bar"},
            is_public=True,
        )
        self.assertIsNotNone(obj.pk)
        self.assertEqual(obj.url, "https://example.org/a.xml")
        self.assertEqual(obj.status, choices.XMLURL_STATUS_SUCCESS)
        self.assertEqual(obj.pid, "pid-v3-0001")
        self.assertEqual(obj.detail, {"foo": "bar"})
        self.assertTrue(obj.is_public)
        self.assertEqual(obj.creator, self.user)

    def test_create_or_update_creates_when_missing(self):
        obj = XMLURL.create_or_update(
            user=self.user,
            url="https://example.org/b.xml",
            status=choices.XMLURL_STATUS_PID_PROVIDER_XML_FAILED,
            pid=None,
            detail={"err": "x"},
            is_public=None,
        )
        self.assertIsNotNone(obj.pk)
        self.assertEqual(obj.status, choices.XMLURL_STATUS_PID_PROVIDER_XML_FAILED)

    def test_create_or_update_updates_existing_partial_fields(self):
        original = XMLURL.create(
            user=self.user,
            url="https://example.org/c.xml",
            status=choices.XMLURL_STATUS_UNEXPECTED_FAILURE,
            pid=None,
            detail={"v": 1},
            is_public=False,
        )
        updated = XMLURL.create_or_update(
            user=self.user,
            url="https://example.org/c.xml",
            status=choices.XMLURL_STATUS_SUCCESS,
            pid="pid-v3-9999",
            # detail=None -> não deve apagar o detail já existente
            detail=None,
            # is_public=None -> não deve sobrescrever o valor já gravado
            is_public=None,
        )
        self.assertEqual(original.pk, updated.pk)
        self.assertEqual(updated.status, choices.XMLURL_STATUS_SUCCESS)
        self.assertEqual(updated.pid, "pid-v3-9999")
        # os dois campos abaixo não deveriam ter sido sobrescritos por None
        self.assertEqual(updated.detail, {"v": 1})
        self.assertFalse(updated.is_public)

    def test_create_or_update_overwrites_when_explicit_values_given(self):
        XMLURL.create(
            user=self.user,
            url="https://example.org/d.xml",
            status=choices.XMLURL_STATUS_UNEXPECTED_FAILURE,
            pid=None,
            detail={"v": 1},
            is_public=False,
        )
        updated = XMLURL.create_or_update(
            user=self.user,
            url="https://example.org/d.xml",
            status=choices.XMLURL_STATUS_SUCCESS,
            pid="pid-v3-1234",
            detail={"v": 2},
            is_public=True,
        )
        self.assertEqual(updated.detail, {"v": 2})
        self.assertTrue(updated.is_public)


class XMLURLSaveFileTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester2", password="x")
        self.obj = XMLURL.create(
            user=self.user,
            url="https://example.org/save-file.xml",
            status=choices.XMLURL_STATUS_SUCCESS,
            pid="pid-v3-0002",
        )
        self.addCleanup(self._delete_uploaded_file)

    def _delete_uploaded_file(self):
        if self.obj.zipfile:
            self.obj.zipfile.delete(save=False)

    def test_save_file_from_str_content(self):
        ok = self.obj.save_file("<article>conteudo</article>", filename="doc.xml")
        self.assertTrue(ok)
        self.assertTrue(self.obj.zipfile.name)

        with zipfile.ZipFile(self.obj.zipfile.path) as zf:
            self.assertIn("doc.xml", zf.namelist())
            content = zf.read("doc.xml").decode("utf-8")
            self.assertEqual(content, "<article>conteudo</article>")

    def test_save_file_from_bytes_content_default_filename(self):
        ok = self.obj.save_file(b"<article>bytes</article>")
        self.assertTrue(ok)
        with zipfile.ZipFile(self.obj.zipfile.path) as zf:
            self.assertIn("content.xml", zf.namelist())

    def test_save_file_returns_false_on_exception(self):
        with patch.object(
            XMLURL, "zipfile", new_callable=MagicMock
        ):
            # Forçando erro dentro do try: zipfile.ZipFile receberá um mock
            # inválido como buffer, o que deve levantar exceção capturada.
            with patch("pid_provider.models.zipfile.ZipFile", side_effect=OSError("boom")):
                ok = self.obj.save_file("<a/>")
                self.assertFalse(ok)


class XMLURLGetStatusTest(TestCase):
    def test_get_status_no_xml_with_pre(self):
        status = XMLURL.get_status(xml_with_pre=None, response={"v3": "x"})
        self.assertEqual(status, choices.XMLURL_STATUS_XML_FETCH_FAILED)

    def test_get_status_no_response(self):
        status = XMLURL.get_status(xml_with_pre=make_xml_with_pre(), response=None)
        self.assertEqual(status, choices.XMLURL_STATUS_UNEXPECTED_FAILURE)

    def test_get_status_response_with_error_type(self):
        status = XMLURL.get_status(
            xml_with_pre=make_xml_with_pre(),
            response={"error_type": "ValueError"},
        )
        self.assertEqual(status, choices.XMLURL_STATUS_PID_PROVIDER_XML_FAILED)

    def test_get_status_response_with_error_msg(self):
        status = XMLURL.get_status(
            xml_with_pre=make_xml_with_pre(),
            response={"error_msg": "deu ruim"},
        )
        self.assertEqual(status, choices.XMLURL_STATUS_PID_PROVIDER_XML_FAILED)

    def test_get_status_response_success(self):
        status = XMLURL.get_status(
            xml_with_pre=make_xml_with_pre(),
            response={"v3": "pid-v3-0001"},
        )
        self.assertEqual(status, choices.XMLURL_STATUS_SUCCESS)


class XMLURLRecordTest(TestCase):
    """
    Cobre os 3 cenários documentados em record():
    a) falha ao obter o XML da URI (xml_with_pre=None, exception setada)
    b) sucesso completo (response preenchido, xml_with_pre setado -> salva zip)
    c) erro inesperado durante o registro (traceback_msg setado)
    """

    def setUp(self):
        self.user = User.objects.create_user(username="tester3", password="x")
        self._created = []
        self.addCleanup(self._cleanup_files)

    def _cleanup_files(self):
        for obj in self._created:
            if obj.zipfile:
                obj.zipfile.delete(save=False)

    def test_record_case_a_xml_fetch_failed(self):
        obj = XMLURL.record(
            user=self.user,
            url="https://example.org/fail-fetch.xml",
            document_item={"status": True},
            exception=ConnectionError("timeout"),
            xml_with_pre=None,
            response=None,
            params={"name": "doc"},
        )
        self._created.append(obj)

        self.assertEqual(obj.status, choices.XMLURL_STATUS_XML_FETCH_FAILED)
        self.assertIsNone(obj.pid)
        self.assertIn("exception", obj.detail)
        self.assertEqual(obj.detail["exception"]["error_type"], str(ConnectionError))
        # is_public inferido de document_item["status"]
        self.assertTrue(obj.is_public)
        # sem xml_with_pre, não deve ter tentado salvar zip
        self.assertFalse(obj.zipfile)

    def test_record_case_b_success_saves_zip(self):
        xwp = make_xml_with_pre(pkg_name="pkg-success", xml_str="<article>ok</article>")
        response = {"v3": "pid-v3-success", "created": True}

        obj = XMLURL.record(
            user=self.user,
            url="https://example.org/success.xml",
            document_item={"status": False},
            exception=None,
            response=response,
            xml_with_pre=xwp,
            params={"name": "doc-ok"},
        )
        self._created.append(obj)

        self.assertEqual(obj.status, choices.XMLURL_STATUS_SUCCESS)
        self.assertEqual(obj.pid, "pid-v3-success")
        self.assertEqual(obj.detail["response"], response)
        self.assertFalse(obj.is_public)  # veio de document_item["status"] = False
        self.assertTrue(obj.zipfile)
        with zipfile.ZipFile(obj.zipfile.path) as zf:
            self.assertIn("pkg-success.xml", zf.namelist())

    def test_record_case_c_unexpected_error_with_traceback(self):
        obj = XMLURL.record(
            user=self.user,
            url="https://example.org/unexpected.xml",
            document_item=None,
            exception=RuntimeError("falhou ao criar PidProviderXML"),
            traceback_msg="Traceback (most recent call last): ...",
            response=None,
            xml_with_pre=make_xml_with_pre(),
            params=None,
        )
        self._created.append(obj)

        self.assertEqual(obj.status, choices.XMLURL_STATUS_UNEXPECTED_FAILURE)
        self.assertIn("traceback", obj.detail)
        self.assertIn("exception", obj.detail)
        # document_item=None -> is_public não deve ser inferido (fica None)
        self.assertIsNone(obj.is_public)

    def test_record_is_idempotent_by_url_via_create_or_update(self):
        url = "https://example.org/idempotent.xml"
        first = XMLURL.record(
            user=self.user,
            url=url,
            document_item=None,
            exception=ConnectionError("primeira falha"),
        )
        self._created.append(first)

        second = XMLURL.record(
            user=self.user,
            url=url,
            document_item=None,
            response={"v3": "pid-v3-ok"},
            xml_with_pre=make_xml_with_pre(pkg_name="pkg-retry"),
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.status, choices.XMLURL_STATUS_SUCCESS)
        self.assertEqual(second.pid, "pid-v3-ok")


class XMLURLDataPropertyTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester4", password="x")

    def _make(self, detail):
        obj = XMLURL()
        obj.user = self.user
        obj.creator = self.user
        obj.url = "https://example.org/data-prop.xml"
        obj.detail = detail
        obj.save()
        return obj

    def test_data_returns_response_when_present(self):
        obj = self._make({"response": {"v3": "abc"}, "exception": {"x": 1}})
        self.assertEqual(obj.data, {"v3": "abc"})

    def test_data_returns_exception_and_traceback_when_no_response(self):
        obj = self._make(
            {
                "exception": {"error_message": "erro", "error_type": "ValueError"},
                "traceback": "tb...",
            }
        )
        self.assertEqual(
            obj.data,
            {
                "error_message": "erro",
                "error_type": "ValueError",
                "traceback": "tb...",
            },
        )

    def test_data_empty_when_no_exception_no_response(self):
        obj = self._make({"params": {"name": "x"}})
        self.assertEqual(obj.data, {})
