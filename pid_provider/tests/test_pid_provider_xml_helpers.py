"""
Testes para métodos auxiliares "puros"/pouco acoplados de PidProviderXML
(pid_provider/models.py): validação de PID, comparação de PIDs registrados,
propriedades de leitura (is_aop, record_status, created_updated,
get_readable_data, data_to_compare, data) e utilitários de consulta
(get_by_pid_v3, get_queryset, delete_queryset, mark_as_waiting/done).

Fluxos mais pesados de negócio (register, select_record, get_best_match)
já têm cobertura própria em outros arquivos deste diretório.
"""
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from pid_provider import exceptions
from pid_provider.models import (
    OtherPid,
    PidProviderXML,
    PidProviderXMLPidV3ConflictError,
)

User = get_user_model()


class IsValidPidLenTests(SimpleTestCase):
    def test_returns_true_for_23_char_value(self):
        self.assertTrue(PidProviderXML.is_valid_pid_len("a" * 23, "pid_v3"))

    def test_raises_value_error_for_wrong_length(self):
        with self.assertRaises(ValueError) as ctx:
            PidProviderXML.is_valid_pid_len("short", "pid_v3")
        self.assertIn("pid_v3", str(ctx.exception))

    def test_raises_value_error_for_falsy_value(self):
        with self.assertRaises(ValueError):
            PidProviderXML.is_valid_pid_len(None, "aop_pid")
        with self.assertRaises(ValueError):
            PidProviderXML.is_valid_pid_len("", "aop_pid")


class IsUpdatedTests(SimpleTestCase):
    """is_updated é @staticmethod: nunca retorna valor -- sinaliza via exceção ou None."""

    def test_force_update_returns_none_regardless_of_other_params(self):
        result = PidProviderXML.is_updated(
            xml_with_pre=MagicMock(), registered=None, force_update=True,
            origin_date=None, registered_in_core=None,
        )
        self.assertIsNone(result)

    def test_not_registered_returns_none(self):
        result = PidProviderXML.is_updated(
            xml_with_pre=MagicMock(), registered=None, force_update=False,
            origin_date=None, registered_in_core=None,
        )
        self.assertIsNone(result)

    def test_needs_registered_in_core_update_returns_none(self):
        registered = MagicMock(registered_in_core=False)
        result = PidProviderXML.is_updated(
            xml_with_pre=MagicMock(), registered=registered, force_update=False,
            origin_date=None, registered_in_core=True,
        )
        self.assertIsNone(result)

    def test_missing_readable_data_returns_none(self):
        registered = MagicMock(registered_in_core=True, readable_data=None)
        result = PidProviderXML.is_updated(
            xml_with_pre=MagicMock(), registered=registered, force_update=False,
            origin_date=None, registered_in_core=None,
        )
        self.assertIsNone(result)

    def test_equal_xml_raises_skip(self):
        registered = MagicMock(registered_in_core=True, readable_data={"x": 1})
        registered.is_equal_to.return_value = True
        with self.assertRaises(exceptions.SkipSavePidProviderXML):
            PidProviderXML.is_updated(
                xml_with_pre=MagicMock(), registered=registered, force_update=False,
                origin_date=None, registered_in_core=None,
            )

    def test_aop_over_vor_raises_forbidden(self):
        registered = MagicMock(registered_in_core=True, readable_data={"x": 1}, is_aop=False)
        registered.is_equal_to.return_value = False
        xml_with_pre = MagicMock(is_aop=True)
        with self.assertRaises(exceptions.ForbiddenPidProviderXMLRegistrationError):
            PidProviderXML.is_updated(
                xml_with_pre=xml_with_pre, registered=registered, force_update=False,
                origin_date=None, registered_in_core=None,
            )

    def test_older_origin_date_raises_skip(self):
        registered = MagicMock(
            registered_in_core=True, readable_data={"x": 1}, is_aop=False, origin_date="2026-02-01"
        )
        registered.is_equal_to.return_value = False
        xml_with_pre = MagicMock(is_aop=False)
        with self.assertRaises(exceptions.SkipSavePidProviderXML):
            PidProviderXML.is_updated(
                xml_with_pre=xml_with_pre, registered=registered, force_update=False,
                origin_date="2026-01-01", registered_in_core=None,
            )

    def test_newer_origin_date_returns_none(self):
        registered = MagicMock(
            registered_in_core=True, readable_data={"x": 1}, is_aop=False, origin_date="2026-01-01"
        )
        registered.is_equal_to.return_value = False
        xml_with_pre = MagicMock(is_aop=False)
        result = PidProviderXML.is_updated(
            xml_with_pre=xml_with_pre, registered=registered, force_update=False,
            origin_date="2026-02-01", registered_in_core=None,
        )
        self.assertIsNone(result)


class CheckRegisteredPidsChangedTests(SimpleTestCase):
    def test_reports_only_fields_that_differ(self):
        ppx = PidProviderXML(v3="V3-OLD", v2="V2-SAME", aop_pid=None)
        xml_with_pre = SimpleNamespace(v3="V3-NEW", v2="V2-SAME", aop_pid="AOP-NEW")

        changed = ppx.check_registered_pids_changed(xml_with_pre)

        by_type = {c["pid_type"]: c for c in changed}
        self.assertEqual(set(by_type), {"pid_v3", "aop_pid"})
        self.assertEqual(by_type["pid_v3"]["pid_in_xml"], "V3-NEW")
        self.assertEqual(by_type["pid_v3"]["registered"], "V3-OLD")
        self.assertEqual(by_type["aop_pid"]["pid_in_xml"], "AOP-NEW")
        self.assertEqual(by_type["aop_pid"]["registered"], None)

    def test_returns_empty_list_when_nothing_changed(self):
        ppx = PidProviderXML(v3="V3", v2="V2", aop_pid="AOP")
        xml_with_pre = SimpleNamespace(v3="V3", v2="V2", aop_pid="AOP")

        self.assertEqual(ppx.check_registered_pids_changed(xml_with_pre), [])


class GetValidPidV3Tests(SimpleTestCase):
    def test_no_xml_pid_returns_registered_pid(self):
        xml_adapter = MagicMock(v3=None)
        result = PidProviderXML.get_valid_pid_v3(xml_adapter, registered_pid="REG-PID")
        self.assertEqual(result, "REG-PID")

    def test_no_xml_pid_and_no_registered_generates_unique(self):
        xml_adapter = MagicMock(v3=None)
        with patch.object(PidProviderXML, "_get_unique_v3", return_value="GENERATED"):
            result = PidProviderXML.get_valid_pid_v3(xml_adapter, registered_pid=None)
        self.assertEqual(result, "GENERATED")

    def test_xml_pid_equal_to_registered_skips_lookup(self):
        xml_adapter = MagicMock(v3="SAME-PID")
        with patch.object(PidProviderXML, "get_record_by_pid_v3") as mock_get:
            result = PidProviderXML.get_valid_pid_v3(xml_adapter, registered_pid="SAME-PID")
        mock_get.assert_not_called()
        self.assertEqual(result, "SAME-PID")

    def test_xml_pid_belongs_to_same_document_is_accepted(self):
        xml_adapter = MagicMock(v3="NEW-PID")
        with patch.object(PidProviderXML, "get_record_by_pid_v3", return_value=MagicMock()):
            result = PidProviderXML.get_valid_pid_v3(xml_adapter, registered_pid="OLD-PID")
        self.assertEqual(result, "NEW-PID")

    def test_xml_pid_unused_is_accepted(self):
        xml_adapter = MagicMock(v3="UNUSED-PID")
        with patch.object(
            PidProviderXML, "get_record_by_pid_v3", side_effect=PidProviderXML.DoesNotExist
        ):
            result = PidProviderXML.get_valid_pid_v3(xml_adapter, registered_pid="OLD-PID")
        self.assertEqual(result, "UNUSED-PID")

    def test_conflict_raises_when_auto_solve_disabled(self):
        xml_adapter = MagicMock(v3="CONFLICTING-PID")
        with patch.object(
            PidProviderXML,
            "get_record_by_pid_v3",
            side_effect=PidProviderXMLPidV3ConflictError("conflict"),
        ):
            with self.assertRaises(PidProviderXMLPidV3ConflictError):
                PidProviderXML.get_valid_pid_v3(
                    xml_adapter, registered_pid="OLD-PID", auto_solve_pid_conflict=False
                )

    def test_conflict_ignored_when_auto_solve_enabled_falls_back_to_registered(self):
        xml_adapter = MagicMock(v3="CONFLICTING-PID")
        with patch.object(
            PidProviderXML,
            "get_record_by_pid_v3",
            side_effect=PidProviderXMLPidV3ConflictError("conflict"),
        ):
            result = PidProviderXML.get_valid_pid_v3(
                xml_adapter, registered_pid="OLD-PID", auto_solve_pid_conflict=True
            )
        self.assertEqual(result, "OLD-PID")


class CompleteMissingXmlPidsTests(SimpleTestCase):
    def _adapter(self, v3=None, v2=None, aop_pid=None):
        xml_with_pre = SimpleNamespace(v3=v3, v2=v2, aop_pid=aop_pid)
        return MagicMock(xml_with_pre=xml_with_pre)

    def test_validates_pid_lengths_before_resolving(self):
        xml_adapter = self._adapter(v3="too-short")
        with self.assertRaises(ValueError):
            PidProviderXML.complete_missing_xml_pids(xml_adapter, registered=None, auto_solve_pid_conflict=True)

    def test_records_pid_v3_change_when_resolved_value_differs(self):
        xml_adapter = self._adapter(v3="a" * 23)
        with patch.object(PidProviderXML, "get_valid_pid_v3", return_value="b" * 23):
            xml_changed = PidProviderXML.complete_missing_xml_pids(
                xml_adapter, registered=None, auto_solve_pid_conflict=True
            )
        self.assertEqual(xml_changed, {"pid_v3": "b" * 23})
        self.assertEqual(xml_adapter.xml_with_pre.v3, "b" * 23)

    def test_no_change_when_resolved_pid_v3_matches_incoming(self):
        pid = "a" * 23
        xml_adapter = self._adapter(v3=pid)
        with patch.object(PidProviderXML, "get_valid_pid_v3", return_value=pid):
            xml_changed = PidProviderXML.complete_missing_xml_pids(
                xml_adapter, registered=None, auto_solve_pid_conflict=True
            )
        self.assertEqual(xml_changed, {})

    def test_fills_missing_v2_and_aop_pid_from_registered(self):
        pid = "a" * 23
        xml_adapter = self._adapter(v3=pid, v2=None, aop_pid=None)
        registered = MagicMock(v3=pid, v2="REG-V2", aop_pid="REG-AOP")
        with patch.object(PidProviderXML, "get_valid_pid_v3", return_value=pid):
            xml_changed = PidProviderXML.complete_missing_xml_pids(
                xml_adapter, registered=registered, auto_solve_pid_conflict=True
            )
        self.assertEqual(xml_changed, {"pid_v2": "REG-V2", "aop_pid": "REG-AOP"})
        self.assertEqual(xml_adapter.xml_with_pre.v2, "REG-V2")
        self.assertEqual(xml_adapter.xml_with_pre.aop_pid, "REG-AOP")

    def test_does_not_overwrite_existing_v2_or_aop_pid(self):
        pid = "a" * 23
        xml_v2 = "b" * 23
        xml_aop = "c" * 23
        xml_adapter = self._adapter(v3=pid, v2=xml_v2, aop_pid=xml_aop)
        registered = MagicMock(v3=pid, v2="REG-V2", aop_pid="REG-AOP")
        with patch.object(PidProviderXML, "get_valid_pid_v3", return_value=pid):
            xml_changed = PidProviderXML.complete_missing_xml_pids(
                xml_adapter, registered=registered, auto_solve_pid_conflict=True
            )
        self.assertEqual(xml_changed, {})
        self.assertEqual(xml_adapter.xml_with_pre.v2, xml_v2)
        self.assertEqual(xml_adapter.xml_with_pre.aop_pid, xml_aop)


class IsAopTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="isaop-user", password="x")

    def test_true_when_no_volume_and_no_number(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A", volume=None, number=None)
        self.assertTrue(ppx.is_aop)

    def test_false_when_volume_present(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="B", volume="10")
        self.assertFalse(ppx.is_aop)

    def test_false_when_number_present(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="C", number="2")
        self.assertFalse(ppx.is_aop)


class RecordStatusAndCreatedUpdatedTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="recstatus-user", password="x")

    def test_freshly_created_object_reports_created_status(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A")
        status = ppx.record_status
        self.assertEqual(status["record_status"], "created")
        self.assertIn("created", status)
        self.assertIn("updated", status)

    def test_updated_long_after_creation_reports_updated_status(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A")
        ppx.updated = ppx.created + timedelta(seconds=10)
        self.assertEqual(ppx.record_status["record_status"], "updated")

    def test_unsaved_instance_has_empty_record_status(self):
        ppx = PidProviderXML(v3="A")
        self.assertEqual(ppx.record_status, {})

    def test_created_updated_prefers_updated(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A")
        self.assertEqual(ppx.created_updated, ppx.updated)

    def test_created_updated_falls_back_to_created_when_no_updated(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A")
        ppx.updated = None
        self.assertEqual(ppx.created_updated, ppx.created)


class GetReadableDataTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="readable-user", password="x")

    def test_returns_stored_readable_data_without_partial_body(self):
        ppx = PidProviderXML.objects.create(
            creator=self.user,
            v3="A",
            readable_data={"article_titles": ["T"], "partial_body": "legacy"},
        )
        result = ppx.get_readable_data()
        self.assertNotIn("partial_body", result)
        self.assertEqual(result["article_titles"], ["T"])

    def test_returns_empty_dict_when_no_readable_data_and_no_current_version(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A", readable_data=None)
        self.assertEqual(ppx.get_readable_data(), {})
        # xml_with_pre falhou (sem current_version) -> marca como inválido
        ppx.refresh_from_db()
        self.assertEqual(ppx.proc_status, "NVALID")


class DataToCompareTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="datacompare-user", password="x")

    def test_includes_titles_and_body_fragment_when_present(self):
        ppx = PidProviderXML.objects.create(
            creator=self.user,
            v3="A",
            z_surnames="Silva",
            z_partial_body="hash-1",
            readable_data={"article_titles": ["T1"], "body_fragment": "frag"},
        )
        data = ppx.data_to_compare
        self.assertEqual(data["article_titles"], ["T1"])
        self.assertEqual(data["body_fragment"], "frag")
        self.assertEqual(data["z_surnames"], "Silva")
        self.assertEqual(data["body_fragment_fingerprint"], "hash-1")

    def test_omits_titles_and_body_fragment_when_absent(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A", readable_data=None)
        data = ppx.data_to_compare
        self.assertNotIn("article_titles", data)
        self.assertNotIn("body_fragment", data)


class DataPropertyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dataprop-user", password="x")

    def test_assembles_expected_keys(self):
        ppx = PidProviderXML.objects.create(
            creator=self.user, v3="V3X", v2="V2X", aop_pid="AOPX", pkg_name="pkg",
            registered_in_core=True,
        )
        data = ppx.data
        self.assertEqual(data["v3"], "V3X")
        self.assertEqual(data["v2"], "V2X")
        self.assertEqual(data["aop_pid"], "AOPX")
        self.assertEqual(data["pkg_name"], "pkg")
        self.assertTrue(data["registered_in_core"])
        self.assertEqual(data["ppx_id"], ppx.id)
        self.assertIn("registered_data", data)
        self.assertEqual(data["record_status"], "created")


class GetByPidV3Tests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="getbypid-user", password="x")

    def test_returns_single_match(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="V3-UNIQUE")
        found = PidProviderXML.get_by_pid_v3("V3-UNIQUE")
        self.assertEqual(found.pk, ppx.pk)

    def test_raises_does_not_exist_when_no_match(self):
        with self.assertRaises(PidProviderXML.DoesNotExist):
            PidProviderXML.get_by_pid_v3("NAO-EXISTE")

    def test_multiple_matches_falls_back_to_most_recently_updated(self):
        older = PidProviderXML.objects.create(creator=self.user, v3="V3-DUP", pkg_name="older")
        newer = PidProviderXML.objects.create(creator=self.user, v3="V3-DUP", pkg_name="newer")
        newer.save()  # garante 'updated' mais recente que 'older'

        found = PidProviderXML.get_by_pid_v3("V3-DUP")

        self.assertEqual(found.pk, newer.pk)


class MarkAsWaitingDoneTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="markstatus-user", password="x")

    def test_mark_as_waiting_updates_status_and_persists(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A", proc_status="TODO")
        ppx.mark_as_waiting()
        ppx.refresh_from_db()
        self.assertEqual(ppx.proc_status, "WAIT")

    def test_mark_as_waiting_is_noop_when_already_waiting(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A", proc_status="WAIT")
        with patch.object(PidProviderXML, "save") as mock_save:
            ppx.mark_as_waiting()
        mock_save.assert_not_called()

    def test_mark_as_done_updates_status_and_persists(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A", proc_status="TODO")
        ppx.mark_as_done()
        ppx.refresh_from_db()
        self.assertEqual(ppx.proc_status, "DONE")

    def test_mark_as_done_is_noop_when_already_done(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A", proc_status="DONE")
        with patch.object(PidProviderXML, "save") as mock_save:
            ppx.mark_as_done()
        mock_save.assert_not_called()


class GetQuerysetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="getqueryset-user", password="x")
        self.match = PidProviderXML.objects.create(
            creator=self.user, v3="A", issn_electronic="0000-1111", pub_year="2026",
            proc_status="TODO",
        )
        self.other_issn = PidProviderXML.objects.create(
            creator=self.user, v3="B", issn_electronic="9999-9999", pub_year="2026",
            proc_status="DONE",
        )
        self.other_year = PidProviderXML.objects.create(
            creator=self.user, v3="C", issn_electronic="0000-1111", pub_year="1999",
        )

    def test_filters_by_issn_list(self):
        qs = PidProviderXML.get_queryset(issn_list=["0000-1111"])
        ids = set(qs.values_list("id", flat=True))
        self.assertIn(self.match.id, ids)
        self.assertNotIn(self.other_issn.id, ids)

    def test_filters_by_pub_year_range(self):
        qs = PidProviderXML.get_queryset(
            issn_list=["0000-1111"], from_pub_year="2020", until_pub_year="2030"
        )
        ids = set(qs.values_list("id", flat=True))
        self.assertIn(self.match.id, ids)
        self.assertNotIn(self.other_year.id, ids)

    def test_filters_by_proc_status_list(self):
        qs = PidProviderXML.get_queryset(proc_status_list=["TODO"])
        ids = set(qs.values_list("id", flat=True))
        self.assertIn(self.match.id, ids)
        self.assertNotIn(self.other_issn.id, ids)


class DeleteQuerysetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="delqueryset-user", password="x")

    def test_deletes_items_and_their_other_pid_records(self):
        ppx = PidProviderXML.objects.create(creator=self.user, v3="A")
        version = ppx.current_version
        OtherPid.objects.create(
            creator=self.user, pid_provider_xml=ppx, pid_type="pid_v3",
            pid_in_xml="OLD", version=version,
        )

        qs = PidProviderXML.objects.filter(pk=ppx.pk)
        PidProviderXML.delete_queryset(qs)

        self.assertFalse(PidProviderXML.objects.filter(pk=ppx.pk).exists())
        self.assertFalse(OtherPid.objects.filter(pid_provider_xml_id=ppx.pk).exists())
