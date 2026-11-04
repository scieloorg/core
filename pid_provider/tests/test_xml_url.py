"""Testes para XMLURL (pid_provider/models.py)."""
import shutil
import tempfile
import zipfile
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, override_settings

from pid_provider.models import XMLURL

User = get_user_model()

MEDIA_ROOT = tempfile.mkdtemp()


class XMLURLGetTests(TestCase):
    def test_raises_value_error_without_url(self):
        with self.assertRaises(ValueError):
            XMLURL.get(url=None)

    def test_raises_does_not_exist_when_no_match(self):
        with self.assertRaises(XMLURL.DoesNotExist):
            XMLURL.get(url="https://example.org/missing")


class XMLURLCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="xmlurl-create", password="x")

    def test_creates_new_record(self):
        obj = XMLURL.create(
            self.user,
            url="https://example.org/a.xml",
            status="pending",
            pid="PID-1",
            detail={"foo": "bar"},
            is_public=True,
        )
        self.assertIsNotNone(obj.pk)
        self.assertEqual(obj.status, "pending")
        self.assertTrue(obj.is_public)

    def test_falls_back_to_get_on_integrity_error(self):
        existing = XMLURL.create(self.user, url="https://example.org/dup.xml")

        with patch.object(XMLURL, "save", side_effect=IntegrityError):
            result = XMLURL.create(self.user, url="https://example.org/dup.xml")

        self.assertEqual(result.pk, existing.pk)


class XMLURLCreateOrUpdateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="xmlurl-cou", password="x")

    def test_creates_when_none_exists(self):
        obj = XMLURL.create_or_update(
            self.user, url="https://example.org/new.xml", status="success"
        )
        self.assertIsNotNone(obj.pk)
        self.assertEqual(obj.status, "success")

    def test_updates_only_fields_explicitly_passed(self):
        existing = XMLURL.create(
            self.user,
            url="https://example.org/upd.xml",
            status="pending",
            pid="OLD-PID",
            is_public=False,
        )

        updated = XMLURL.create_or_update(
            self.user,
            url="https://example.org/upd.xml",
            status="success",
            # pid, detail, is_public não passados (None) -> preservados
        )

        self.assertEqual(updated.pk, existing.pk)
        self.assertEqual(updated.status, "success")
        self.assertEqual(updated.pid, "OLD-PID")
        self.assertFalse(updated.is_public)
        self.assertEqual(updated.updated_by, self.user)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class XMLURLSaveFileTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user(username="xmlurl-savefile", password="x")
        self.obj = XMLURL.create(self.user, url="https://example.org/savefile.xml", pid="PID-9")

    def test_save_file_success_writes_readable_zip(self):
        result = self.obj.save_file("<article/>", filename="doc.xml")

        self.assertTrue(result)
        self.obj.refresh_from_db()
        self.assertTrue(self.obj.zipfile.name)
        with zipfile.ZipFile(self.obj.zipfile.path) as zf:
            self.assertEqual(zf.namelist(), ["doc.xml"])
            self.assertEqual(zf.read("doc.xml"), b"<article/>")

    def test_save_file_accepts_bytes_content(self):
        result = self.obj.save_file(b"<article/>")
        self.assertTrue(result)

    def test_save_file_returns_false_on_failure(self):
        with patch("pid_provider.models.zipfile.ZipFile", side_effect=OSError("boom")):
            result = self.obj.save_file("<article/>")
        self.assertFalse(result)


class XMLURLRecordTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="xmlurl-record", password="x")

    def test_record_creates_new_with_pid_from_response(self):
        obj = XMLURL.record(
            user=self.user,
            url="https://example.org/rec.xml",
            status="success",
            document_item={"status": "true"},
            response={"v3": "PID-FROM-RESPONSE"},
        )

        self.assertEqual(obj.pid, "PID-FROM-RESPONSE")
        self.assertEqual(obj.detail["response"], {"v3": "PID-FROM-RESPONSE"})
        self.assertTrue(obj.is_public)

    def test_record_is_public_false_when_status_is_the_string_false(self):
        obj = XMLURL.record(
            user=self.user,
            url="https://example.org/rec2.xml",
            status="success",
            document_item={"status": "false"},
        )
        self.assertFalse(obj.is_public)

    def test_record_is_public_none_when_no_document_item(self):
        obj = XMLURL.record(
            user=self.user,
            url="https://example.org/rec3.xml",
            status="success",
            document_item=None,
        )
        self.assertIsNone(obj.is_public)

    def test_record_stores_exception_traceback_in_detail(self):
        obj = XMLURL.record(
            user=self.user,
            url="https://example.org/rec4.xml",
            status="xml_fetch_failed",
            document_item={"info": "x"},
            exception=True,
        )
        self.assertIn("exceptions", obj.detail)

    @override_settings(MEDIA_ROOT=MEDIA_ROOT)
    def test_record_saves_file_when_xml_with_pre_given(self):
        fake_xml_with_pre = MagicMock()
        fake_xml_with_pre.tostring.return_value = "<article/>"

        with patch.object(XMLURL, "save_file") as mock_save_file:
            obj = XMLURL.record(
                user=self.user,
                url="https://example.org/rec5.xml",
                status="success",
                document_item={"status": "true"},
                response={"v3": "PID-5"},
                xml_with_pre=fake_xml_with_pre,
            )

        mock_save_file.assert_called_once_with("<article/>", filename="PID-5")
        self.assertEqual(obj.pid, "PID-5")
