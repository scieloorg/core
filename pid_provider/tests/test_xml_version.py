"""
Testes para XMLVersion (pid_provider/models.py).

XMLVersion.create/get_or_create/save_file lidam com um FileField real, então
os testes que gravam arquivo usam override_settings(MEDIA_ROOT=<tmp>) para
não sujar o MEDIA_ROOT do projeto.

A property xml_with_pre (que depende de packtools.XMLWithPre.create) e a
cached_property xml são testadas com XMLWithPre.create / xml_with_pre
mockados -- não é objetivo destes testes validar o parsing real de XML, e
sim o contrato de XMLVersion ao redor dele.
"""
import shutil
import tempfile
from unittest.mock import MagicMock, PropertyMock, patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, override_settings

from pid_provider.models import (
    PidProviderXML,
    XMLVersion,
    XMLVersionGetError,
    XMLVersionXmlWithPreError,
)

User = get_user_model()

MEDIA_ROOT = tempfile.mkdtemp()


def make_xml_with_pre(finger_print="fp-1", v3="ABCDEFGHIJKLMNOPQRSTUVW"):
    xml_with_pre = MagicMock(name="xml_with_pre")
    xml_with_pre.finger_print = finger_print
    xml_with_pre.tostring.return_value = "<article/>"
    xml_with_pre.v3 = v3
    return xml_with_pre


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class XMLVersionMediaTestCase(TestCase):
    """Base com limpeza do MEDIA_ROOT temporário usado pelos testes que gravam arquivo."""

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user(username=f"user-{id(self)}", password="x")
        # pkg_name é obrigatório para xml_directory_path (upload_to do FileField)
        self.ppx = PidProviderXML.objects.create(
            creator=self.user, v3="ABC", pkg_name="pkg-fake"
        )


class XMLVersionCreateTests(XMLVersionMediaTestCase):
    def test_create_sets_finger_print_creator_and_saves_file(self):
        xml_with_pre = make_xml_with_pre(finger_print="fp-abc")

        version = XMLVersion.create(self.user, self.ppx, xml_with_pre)

        self.assertEqual(version.finger_print, "fp-abc")
        self.assertEqual(version.creator, self.user)
        self.assertEqual(version.pid_provider_xml, self.ppx)
        self.assertTrue(version.file.name.endswith(".xml"))

    def test_create_falls_back_to_get_on_integrity_error(self):
        """
        IntegrityError ao salvar (ex.: corrida entre requisições concorrentes
        criando a mesma versão) faz create() recuperar o registro já
        existente via get(pid_provider_xml, finger_print), em vez de
        propagar o erro.
        """
        xml_with_pre = make_xml_with_pre(finger_print="fp-dup")
        existing = XMLVersion.create(self.user, self.ppx, xml_with_pre)

        with patch.object(XMLVersion, "save", side_effect=IntegrityError):
            result = XMLVersion.create(self.user, self.ppx, xml_with_pre)

        self.assertEqual(result.pk, existing.pk)


class XMLVersionIsEqualToTests(XMLVersionMediaTestCase):
    def test_is_equal_to_true_when_finger_print_matches_and_file_exists(self):
        version = XMLVersion.create(self.user, self.ppx, make_xml_with_pre(finger_print="same-fp"))

        self.assertTrue(version.is_equal_to(make_xml_with_pre(finger_print="same-fp")))

    def test_is_equal_to_false_when_finger_print_differs(self):
        version = XMLVersion.create(self.user, self.ppx, make_xml_with_pre(finger_print="fp-a"))

        self.assertFalse(version.is_equal_to(make_xml_with_pre(finger_print="fp-b")))


class XMLVersionXmlWithPreTests(TestCase):
    def test_raises_xml_version_error_when_file_has_no_path(self):
        """
        Sem arquivo associado, self.file.path levanta ValueError -- capturado
        pelo `except Exception` genérico da property e relançado como
        XMLVersionXmlWithPreError (mensagem inclui o v3 do pid_provider_xml).
        """
        version = XMLVersion(pid_provider_xml=PidProviderXML(v3="ABC-V3"))

        with self.assertRaises(XMLVersionXmlWithPreError) as ctx:
            version.xml_with_pre
        self.assertIn("ABC-V3", str(ctx.exception))

    def test_raises_xml_version_error_when_xml_with_pre_create_fails(self):
        version = XMLVersion(pid_provider_xml=PidProviderXML(v3="ABC"))
        version.file.name = "some/path.xml"

        with patch("pid_provider.models.XMLWithPre.create", side_effect=Exception("boom")):
            with self.assertRaises(XMLVersionXmlWithPreError):
                version.xml_with_pre

    def test_returns_first_item_from_xml_with_pre_create(self):
        version = XMLVersion(pid_provider_xml=PidProviderXML(v3="ABC"))
        version.file.name = "some/path.xml"
        item1, item2 = MagicMock(name="item1"), MagicMock(name="item2")

        with patch("pid_provider.models.XMLWithPre.create", return_value=[item1, item2]):
            self.assertIs(version.xml_with_pre, item1)


class XMLVersionXmlCachedPropertyTests(TestCase):
    """
    `xml` é uma cached_property que delega para a property `xml_with_pre`
    (não cacheada), então cada teste usa uma instância nova para evitar
    reaproveitar o cache entre casos.
    """

    def test_returns_string_on_success(self):
        version = XMLVersion(pid_provider_xml=PidProviderXML(v3="ABC"))
        fake_xml_with_pre = MagicMock()
        fake_xml_with_pre.tostring.return_value = "<article/>"

        with patch.object(
            XMLVersion, "xml_with_pre", new_callable=PropertyMock
        ) as mock_prop:
            mock_prop.return_value = fake_xml_with_pre
            self.assertEqual(version.xml, "<article/>")

    def test_returns_error_string_when_xml_with_pre_raises(self):
        version = XMLVersion(pid_provider_xml=PidProviderXML(v3="ABC"))

        with patch.object(
            XMLVersion, "xml_with_pre", new_callable=PropertyMock
        ) as mock_prop:
            mock_prop.side_effect = XMLVersionXmlWithPreError("deu erro")
            self.assertEqual(version.xml, "deu erro")

    def test_returns_none_when_file_not_found(self):
        version = XMLVersion(pid_provider_xml=PidProviderXML(v3="ABC"))

        with patch.object(
            XMLVersion, "xml_with_pre", new_callable=PropertyMock
        ) as mock_prop:
            mock_prop.side_effect = FileNotFoundError
            self.assertIsNone(version.xml)


class XMLVersionGetTests(XMLVersionMediaTestCase):
    def test_get_raises_when_missing_pid_provider_xml_or_finger_print(self):
        with self.assertRaises(XMLVersionGetError):
            XMLVersion.get(None, "fp")
        with self.assertRaises(XMLVersionGetError):
            XMLVersion.get(self.ppx, None)

    def test_get_returns_latest_matching_finger_print(self):
        created = XMLVersion.create(self.user, self.ppx, make_xml_with_pre(finger_print="fp-x"))

        found = XMLVersion.get(self.ppx, "fp-x")

        self.assertEqual(found.pk, created.pk)

    def test_get_raises_does_not_exist_when_no_match(self):
        with self.assertRaises(XMLVersion.DoesNotExist):
            XMLVersion.get(self.ppx, "nao-existe")


class XMLVersionGetOrCreateTests(XMLVersionMediaTestCase):
    def test_creates_new_when_none_exists(self):
        xml_with_pre = make_xml_with_pre(finger_print="fp-new")

        version = XMLVersion.get_or_create(self.user, self.ppx, xml_with_pre)

        self.assertEqual(version.finger_print, "fp-new")
        self.assertTrue(XMLVersion.objects.filter(pk=version.pk).exists())

    def test_returns_latest_when_file_still_exists(self):
        xml_with_pre = make_xml_with_pre(finger_print="fp-keep")
        created = XMLVersion.create(self.user, self.ppx, xml_with_pre)

        with patch.object(XMLVersion, "save_file") as mock_save_file:
            found = XMLVersion.get_or_create(self.user, self.ppx, xml_with_pre)

        self.assertEqual(found.pk, created.pk)
        mock_save_file.assert_not_called()

    def test_resaves_file_when_latest_exists_but_file_missing(self):
        xml_with_pre = make_xml_with_pre(finger_print="fp-missing-file")
        created = XMLVersion.create(self.user, self.ppx, xml_with_pre)
        # simula arquivo removido do storage sem remover o registro
        created.file.delete(save=True)

        found = XMLVersion.get_or_create(self.user, self.ppx, xml_with_pre)

        self.assertEqual(found.pk, created.pk)
        self.assertTrue(found.file.name)
