"""
Testes para operações de manutenção/consulta de PidProviderXML
(pid_provider/models.py): _is_registered_pid, get_record_by_pid_v3,
add_collections, mark_items_as_invalid, find_duplicated_pkg_names,
mark_items_as_duplicated, deduplicate_items, fix_duplicated_pkg_name,
fix_pkg_name, is_registered, public_items, xml_with_pre/get_xml_with_pre,
fix_pid_v2.
"""
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from collection.models import Collection
from journal.models import Journal, OfficialJournal
from pid_provider import choices, exceptions
from pid_provider.models import OtherPid, PidProviderXML, XMLVersion

User = get_user_model()


class IsRegisteredPidTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="isregpid-user", password="x")

    def test_returns_none_when_no_pid_given(self):
        self.assertIsNone(PidProviderXML._is_registered_pid())

    def test_true_when_v3_matches_directly(self):
        PidProviderXML.objects.create(creator=self.user, v3="V3-DIRECT")
        self.assertTrue(PidProviderXML._is_registered_pid(v3="V3-DIRECT"))

    def test_true_when_v3_matches_other_pid(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="V3-CURRENT")
        OtherPid.objects.create(
            creator=self.user, pid_provider_xml=ppx, pid_type="pid_v3", pid_in_xml="V3-LEGACY"
        )
        self.assertTrue(PidProviderXML._is_registered_pid(v3="V3-LEGACY"))

    def test_false_when_v3_unused(self):
        self.assertFalse(PidProviderXML._is_registered_pid(v3="NAO-EXISTE"))

    def test_true_when_v2_matches_directly(self):
        PidProviderXML.objects.create(creator=self.user, v3="V3-X", v2="V2-DIRECT")
        self.assertTrue(PidProviderXML._is_registered_pid(v2="V2-DIRECT"))

    def test_true_when_aop_pid_matches_v2_or_aop_pid_field(self):
        PidProviderXML.objects.create(creator=self.user, v3="V3-Y", aop_pid="AOP-1")
        self.assertTrue(PidProviderXML._is_registered_pid(aop_pid="AOP-1"))
        PidProviderXML.objects.create(creator=self.user, v3="V3-Z", v2="AOP-2")
        self.assertTrue(PidProviderXML._is_registered_pid(aop_pid="AOP-2"))


class GetRecordByPidV3Tests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="getrecord-user", password="x")

    def test_raises_value_error_when_adapter_has_no_v3(self):
        xml_adapter = MagicMock(v3=None)
        with self.assertRaises(ValueError):
            PidProviderXML.get_record_by_pid_v3(xml_adapter)

    def test_raises_does_not_exist_when_pid_is_unused(self):
        xml_adapter = MagicMock(v3="UNUSED-PID")
        xml_adapter.get_data_to_compare.return_value = {}
        xml_adapter.xml_with_pre.body_fragment_fingerprint = None
        with self.assertRaises(PidProviderXML.DoesNotExist):
            PidProviderXML.get_record_by_pid_v3(xml_adapter)

    def test_returns_registered_when_best_match_approves(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="V3-MATCH")
        xml_adapter = MagicMock(v3="V3-MATCH")
        xml_adapter.get_data_to_compare.return_value = {}
        xml_adapter.xml_with_pre.body_fragment_fingerprint = None

        with patch.object(
            PidProviderXML, "get_best_match", return_value={"registered": ppx}
        ):
            result = PidProviderXML.get_record_by_pid_v3(xml_adapter)

        self.assertEqual(result, ppx)

    def test_raises_conflict_when_best_match_does_not_approve(self):
        PidProviderXML.objects.create(creator=self.user, v3="V3-CONFLICT")
        xml_adapter = MagicMock(v3="V3-CONFLICT")
        xml_adapter.get_data_to_compare.return_value = {}
        xml_adapter.xml_with_pre.body_fragment_fingerprint = None

        with patch.object(PidProviderXML, "get_best_match", return_value={}):
            with self.assertRaises(Exception) as ctx:
                PidProviderXML.get_record_by_pid_v3(xml_adapter)
        from pid_provider.models import PidProviderXMLPidV3ConflictError
        self.assertIsInstance(ctx.exception, PidProviderXMLPidV3ConflictError)


class MarkItemsAsInvalidTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="markinvalid-user", password="x")

    def test_marks_items_without_valid_xml_as_invalid(self):
        # sem current_version -> xml_with_pre falha -> valid=False -> marca NVALID
        ppx = PidProviderXML.objects.create(
            creator=self.user, v3="A", issn_print="1111-1111", proc_status="TODO"
        )

        PidProviderXML.mark_items_as_invalid(["1111-1111"])

        ppx.refresh_from_db()
        self.assertEqual(ppx.proc_status, choices.PPXML_STATUS_INVALID)

    def test_does_not_touch_items_with_other_issns(self):
        ppx = PidProviderXML.objects.create(
            creator=self.user, v3="B", issn_print="2222-2222", proc_status="TODO"
        )

        PidProviderXML.mark_items_as_invalid(["1111-1111"])

        ppx.refresh_from_db()
        self.assertEqual(ppx.proc_status, "TODO")

    def test_valid_item_is_left_untouched(self):
        ppx = PidProviderXML.objects.create(
            creator=self.user, v3="C", issn_print="3333-3333", proc_status="TODO"
        )
        with patch(
            "pid_provider.models.PidProviderXML.xml_with_pre",
            new_callable=lambda: property(lambda self: "<article/>"),
        ):
            PidProviderXML.mark_items_as_invalid(["3333-3333"])

        ppx.refresh_from_db()
        self.assertEqual(ppx.proc_status, "TODO")


class FindAndMarkDuplicatedTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dup-user", password="x")

    def test_find_duplicated_pkg_names_detects_repeated_names(self):
        PidProviderXML.objects.create(
            creator=self.user, v3="A", issn_print="4444-4444", pkg_name="pkg-dup"
        )
        PidProviderXML.objects.create(
            creator=self.user, v3="B", issn_print="4444-4444", pkg_name="pkg-dup"
        )
        PidProviderXML.objects.create(
            creator=self.user, v3="C", issn_print="4444-4444", pkg_name="pkg-unique"
        )

        result = PidProviderXML.find_duplicated_pkg_names(["4444-4444"])

        self.assertEqual(result, ["pkg-dup"])

    def test_find_duplicated_pkg_names_excludes_already_flagged_items(self):
        PidProviderXML.objects.create(
            creator=self.user, v3="D", issn_print="5555-5555", pkg_name="pkg-x",
            proc_status=choices.PPXML_STATUS_DUPLICATED,
        )
        PidProviderXML.objects.create(
            creator=self.user, v3="E", issn_print="5555-5555", pkg_name="pkg-x",
            proc_status=choices.PPXML_STATUS_DUPLICATED,
        )

        result = PidProviderXML.find_duplicated_pkg_names(["5555-5555"])

        self.assertEqual(result, [])

    def test_mark_items_as_duplicated_flags_all_matching_pkg_name(self):
        a = PidProviderXML.objects.create(
            creator=self.user, v3="F", issn_print="6666-6666", pkg_name="pkg-y"
        )
        b = PidProviderXML.objects.create(
            creator=self.user, v3="G", issn_print="6666-6666", pkg_name="pkg-y"
        )

        result = PidProviderXML.mark_items_as_duplicated(["6666-6666"])

        self.assertEqual(result, ["pkg-y"])
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual(a.proc_status, choices.PPXML_STATUS_DUPLICATED)
        self.assertEqual(b.proc_status, choices.PPXML_STATUS_DUPLICATED)

    def test_mark_items_as_duplicated_returns_none_when_nothing_duplicated(self):
        result = PidProviderXML.mark_items_as_duplicated(["7777-7777"])
        self.assertIsNone(result)


class FixDuplicatedPkgNameTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fixdup-user", password="x")

    def test_keeps_most_recent_and_records_other_pid_for_the_rest(self):
        """
        OtherPid.get_or_create EXIGE version truthy -- por isso `older`
        precisa de um current_version real, senão a chamada dentro de
        fix_duplicated_pkg_name levanta ValueError, que é silenciosamente
        capturado pelo `except Exception` do próprio método (vira
        UnexpectedEvent, sem propagar), deixando o OtherPid por criar.
        """
        older = PidProviderXML.objects.create(
            creator=self.user, v3="V3-OLDER", pkg_name="pkg-fix"
        )
        older_version = XMLVersion.objects.create(creator=self.user, pid_provider_xml=older)
        older.current_version = older_version
        older.save()

        newer = PidProviderXML.objects.create(
            creator=self.user, v3="V3-NEWER", pkg_name="pkg-fix"
        )
        newer.save()  # garante updated mais recente

        PidProviderXML.fix_duplicated_pkg_name("pkg-fix", self.user)

        newer.refresh_from_db()
        self.assertEqual(newer.proc_status, choices.PPXML_STATUS_DEDUPLICATED)
        self.assertTrue(
            OtherPid.objects.filter(
                pid_provider_xml=newer, pid_type="pid_v3", pid_in_xml="V3-OLDER"
            ).exists()
        )

    def test_swallows_error_when_older_item_has_no_current_version(self):
        """
        Documenta o comportamento real: sem current_version, o OtherPid do
        item mais antigo não pode ser criado (version obrigatório) --
        fix_duplicated_pkg_name captura a exceção internamente (via
        UnexpectedEvent.create) e não propaga, mas também não cria o
        OtherPid nem levanta erro para o chamador.
        """
        PidProviderXML.objects.create(
            creator=self.user, v3="V3-OLDER-NOVERSION", pkg_name="pkg-fix-noversion"
        )
        newer = PidProviderXML.objects.create(
            creator=self.user, v3="V3-NEWER-NOVERSION", pkg_name="pkg-fix-noversion"
        )
        newer.save()

        PidProviderXML.fix_duplicated_pkg_name("pkg-fix-noversion", self.user)  # não deve propagar

        newer.refresh_from_db()
        self.assertEqual(newer.proc_status, choices.PPXML_STATUS_DEDUPLICATED)
        self.assertFalse(
            OtherPid.objects.filter(
                pid_provider_xml=newer, pid_in_xml="V3-OLDER-NOVERSION"
            ).exists()
        )

    def test_noop_when_less_than_two_items_share_pkg_name(self):
        PidProviderXML.objects.create(creator=self.user, v3="V3-SOLO", pkg_name="pkg-solo")
        result = PidProviderXML.fix_duplicated_pkg_name("pkg-solo", self.user)
        self.assertEqual(result, 0)


class FixPkgNameTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fixpkgname-user", password="x")

    def test_updates_when_pkg_name_differs(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A", pkg_name="old-name")
        result = ppx.fix_pkg_name("new-name")
        self.assertTrue(result)
        ppx.refresh_from_db()
        self.assertEqual(ppx.pkg_name, "new-name")

    def test_returns_false_when_pkg_name_unchanged(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A", pkg_name="same-name")
        result = ppx.fix_pkg_name("same-name")
        self.assertFalse(result)

    def test_falls_back_to_xml_with_pre_sps_pkg_name_when_no_pkg_name_given(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A", pkg_name="old-name")
        fake_xml_with_pre = MagicMock(sps_pkg_name="derived-name")
        with patch.object(
            PidProviderXML, "xml_with_pre", new_callable=lambda: property(lambda self: fake_xml_with_pre)
        ):
            result = ppx.fix_pkg_name(None)
        self.assertTrue(result)
        self.assertEqual(ppx.pkg_name, "derived-name")


class IsRegisteredTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="isregistered-user", password="x")

    def test_returns_registered_false_when_not_found(self):
        xml_with_pre = MagicMock()
        xml_with_pre.data = {}
        xml_with_pre.filename = "file.xml"

        with patch("packtools.sps.pid_provider.xml_sps_adapter.PidProviderXMLAdapter") as MockAdapter:
            mock_adapter = MockAdapter.return_value
            mock_adapter.data = {}
            with patch.object(PidProviderXML, "select_records", return_value=iter([])):
                response = PidProviderXML.is_registered(xml_with_pre)

        self.assertFalse(response["registered"])
        self.assertEqual(response["filename"], "file.xml")

    def test_returns_registered_true_with_is_equal_flag(self):
        xml_with_pre = MagicMock()
        xml_with_pre.data = {}

        registered = MagicMock()
        registered.data = {"v3": "V3-X"}
        registered.readable_data = {"x": 1}
        registered.is_equal_to.return_value = True

        with patch("packtools.sps.pid_provider.xml_sps_adapter.PidProviderXMLAdapter") as MockAdapter:
            MockAdapter.return_value.data = {}
            with patch.object(PidProviderXML, "select_records", return_value=iter([])), \
                 patch.object(
                     PidProviderXML, "select_record",
                     return_value={"registered": registered},
                 ):
                response = PidProviderXML.is_registered(xml_with_pre)

        self.assertTrue(response["registered"])
        self.assertTrue(response["is_equal"])

    def test_is_equal_forced_false_when_no_readable_data(self):
        xml_with_pre = MagicMock()
        xml_with_pre.data = {}

        registered = MagicMock()
        registered.data = {"v3": "V3-X"}
        registered.readable_data = None
        registered.is_equal_to.return_value = True

        with patch("packtools.sps.pid_provider.xml_sps_adapter.PidProviderXMLAdapter") as MockAdapter:
            MockAdapter.return_value.data = {}
            with patch.object(PidProviderXML, "select_records", return_value=iter([])), \
                 patch.object(
                     PidProviderXML, "select_record",
                     return_value={"registered": registered},
                 ):
                response = PidProviderXML.is_registered(xml_with_pre)

        self.assertFalse(response["is_equal"])

    def test_returns_error_keys_on_unexpected_exception(self):
        xml_with_pre = MagicMock()
        xml_with_pre.data = {}

        with patch(
            "packtools.sps.pid_provider.xml_sps_adapter.PidProviderXMLAdapter",
            side_effect=ValueError("boom"),
        ):
            response = PidProviderXML.is_registered(xml_with_pre)

        self.assertIn("error_msg", response)
        self.assertIn("error_type", response)


class PublicItemsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="public-user", password="x")

    def test_excludes_items_without_current_version_pid_v3(self):
        PidProviderXML.objects.create(creator=self.user, v3="A")
        from_date = (timezone.now() - timedelta(days=1)).isoformat()

        items = list(PidProviderXML.public_items(from_date))

        self.assertEqual(items, [])

    def test_includes_available_and_recently_updated_item(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A")
        version = XMLVersion.objects.create(creator=self.user, pid_provider_xml=ppx)
        ppx.current_version = version
        ppx.save()

        from_date = (timezone.now() - timedelta(days=1)).isoformat()
        items = list(PidProviderXML.public_items(from_date))

        self.assertIn(ppx.id, [item.id for item in items])

    def test_excludes_item_not_yet_available(self):
        ppx = PidProviderXML.objects.create(
            creator=self.user, v3="A",
            available_since=(timezone.now() + timedelta(days=30)).isoformat()[:10],
        )
        version = XMLVersion.objects.create(creator=self.user, pid_provider_xml=ppx)
        ppx.current_version = version
        ppx.save()

        from_date = (timezone.now() - timedelta(days=1)).isoformat()
        items = list(PidProviderXML.public_items(from_date))

        self.assertNotIn(ppx.id, [item.id for item in items])


class XmlWithPreInstancePropertyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="xmlwithpre-user", password="x")

    def test_returns_none_and_marks_invalid_when_current_version_missing(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A", proc_status="TODO")

        result = ppx.xml_with_pre

        self.assertIsNone(result)
        ppx.refresh_from_db()
        self.assertEqual(ppx.proc_status, choices.PPXML_STATUS_INVALID)

    def test_returns_current_version_xml_with_pre_when_available(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A")
        version = XMLVersion.objects.create(creator=self.user, pid_provider_xml=ppx)
        ppx.current_version = version
        ppx.save()

        fake_xml_with_pre = MagicMock()
        with patch.object(
            XMLVersion, "xml_with_pre", new_callable=lambda: property(lambda self: fake_xml_with_pre)
        ):
            self.assertIs(ppx.xml_with_pre, fake_xml_with_pre)

    def test_get_xml_with_pre_returns_none_when_v3_missing(self):
        self.assertIsNone(PidProviderXML.get_xml_with_pre("NAO-EXISTE"))

    def test_get_xml_with_pre_delegates_to_instance_property(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="V3-GET")
        version = XMLVersion.objects.create(creator=self.user, pid_provider_xml=ppx)
        ppx.current_version = version
        ppx.save()

        fake_xml_with_pre = MagicMock()
        with patch.object(
            XMLVersion, "xml_with_pre", new_callable=lambda: property(lambda self: fake_xml_with_pre)
        ):
            self.assertIs(PidProviderXML.get_xml_with_pre("V3-GET"), fake_xml_with_pre)


class FixPidV2MethodTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fixpidv2method-user", password="x")

    def test_raises_does_not_exist_with_context_when_pid_missing(self):
        with self.assertRaises(PidProviderXML.DoesNotExist):
            PidProviderXML.fix_pid_v2(self.user, "NAO-EXISTE", "V2-NEW")

    def test_returns_data_unchanged_when_correct_equals_current(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="V3-SAME", v2="V2-SAME")

        result = PidProviderXML.fix_pid_v2(self.user, "V3-SAME", "V2-SAME")

        self.assertEqual(result["v2"], "V2-SAME")

    def test_updates_v2_and_current_version_xml(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="V3-FIX", v2="V2-OLD")
        version = XMLVersion.objects.create(creator=self.user, pid_provider_xml=ppx)
        ppx.current_version = version
        ppx.save()

        fake_xml_with_pre = MagicMock()
        with patch.object(
            XMLVersion, "xml_with_pre", new_callable=lambda: property(lambda self: fake_xml_with_pre)
        ), patch.object(PidProviderXML, "_add_current_version") as mock_add_version:
            result = PidProviderXML.fix_pid_v2(self.user, "V3-FIX", "V2-NEW")

        self.assertEqual(fake_xml_with_pre.v2, "V2-NEW")
        mock_add_version.assert_called_once()
        ppx.refresh_from_db()
        self.assertEqual(ppx.v2, "V2-NEW")
        self.assertEqual(result["v2"], "V2-NEW")

    def test_wraps_unexpected_error_in_fix_pid_v2_error(self):
        PidProviderXML.objects.create(creator=self.user, v3="V3-ERR", v2="V2-OLD")

        with patch.object(
            PidProviderXML, "_add_current_version", side_effect=ValueError("boom")
        ), patch.object(
            XMLVersion, "xml_with_pre", new_callable=lambda: property(lambda self: MagicMock())
        ), self.assertRaises(exceptions.PidProviderXMLFixPidV2Error):
            # precisa de current_version setado para chegar em xml_with_pre
            ppx = PidProviderXML.objects.get(v3="V3-ERR")
            version = XMLVersion.objects.create(creator=self.user, pid_provider_xml=ppx)
            ppx.current_version = version
            ppx.save()
            PidProviderXML.fix_pid_v2(self.user, "V3-ERR", "V2-NEW")
