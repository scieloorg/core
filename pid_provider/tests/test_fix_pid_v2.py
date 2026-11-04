"""Testes para FixPidV2 (pid_provider/models.py)."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from pid_provider.models import FixPidV2, PidProviderXML

User = get_user_model()


class FixPidV2GetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fixpid-user", password="x")
        self.ppx = PidProviderXML.objects.create(creator=self.user, v3="ABC", v2="V2-OLD")

    def test_raises_value_error_when_pid_provider_xml_is_falsy(self):
        with self.assertRaises(ValueError):
            FixPidV2.get(pid_provider_xml=None)

    def test_raises_does_not_exist_when_no_record(self):
        with self.assertRaises(FixPidV2.DoesNotExist):
            FixPidV2.get(pid_provider_xml=self.ppx)


class FixPidV2CreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fixpid-create", password="x")
        self.ppx = PidProviderXML.objects.create(creator=self.user, v3="ABC", v2="V2-OLD")

    def test_raises_value_error_when_correct_equals_incorrect(self):
        with self.assertRaises(ValueError):
            FixPidV2.create(
                self.user, self.ppx, incorrect_pid_v2="V2-OLD", correct_pid_v2="V2-OLD"
            )

    def test_raises_value_error_when_correct_pid_v2_missing(self):
        with self.assertRaises(ValueError):
            FixPidV2.create(
                self.user, self.ppx, incorrect_pid_v2="V2-OLD", correct_pid_v2=None
            )

    def test_raises_value_error_when_incorrect_pid_v2_missing(self):
        with self.assertRaises(ValueError):
            FixPidV2.create(
                self.user, self.ppx, incorrect_pid_v2=None, correct_pid_v2="V2-NEW"
            )

    def test_creates_new_record(self):
        obj = FixPidV2.create(
            self.user,
            self.ppx,
            incorrect_pid_v2="V2-OLD",
            correct_pid_v2="V2-NEW",
            fixed_in_core=False,
            fixed_in_upload=True,
        )

        self.assertIsNotNone(obj.pk)
        self.assertEqual(obj.incorrect_pid_v2, "V2-OLD")
        self.assertEqual(obj.correct_pid_v2, "V2-NEW")
        self.assertTrue(obj.fixed_in_upload)

    def test_falls_back_to_get_on_integrity_error(self):
        existing = FixPidV2.create(
            self.user, self.ppx, incorrect_pid_v2="V2-OLD", correct_pid_v2="V2-NEW"
        )

        with patch.object(FixPidV2, "save", side_effect=IntegrityError):
            result = FixPidV2.create(
                self.user, self.ppx, incorrect_pid_v2="V2-OLD", correct_pid_v2="V2-OTHER"
            )

        self.assertEqual(result.pk, existing.pk)


class FixPidV2CreateOrUpdateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fixpid-cou", password="x")
        self.ppx = PidProviderXML.objects.create(creator=self.user, v3="ABC", v2="V2-OLD")

    def test_creates_when_none_exists(self):
        obj = FixPidV2.create_or_update(
            self.user,
            self.ppx,
            incorrect_pid_v2="V2-OLD",
            correct_pid_v2="V2-NEW",
            fixed_in_core=True,
            fixed_in_upload=False,
        )
        self.assertIsNotNone(obj.pk)
        self.assertTrue(obj.fixed_in_core)

    def test_updates_existing_merging_truthy_flags_only(self):
        """
        fixed_in_core/fixed_in_upload são combinados com `novo or antigo`:
        um novo valor falsy (None/False) NÃO apaga um valor truthy já
        persistido.
        """
        existing = FixPidV2.create(
            self.user,
            self.ppx,
            incorrect_pid_v2="V2-OLD",
            correct_pid_v2="V2-NEW",
            fixed_in_core=True,
            fixed_in_upload=None,
        )

        updated = FixPidV2.create_or_update(
            self.user,
            self.ppx,
            fixed_in_core=None,
            fixed_in_upload=True,
        )

        self.assertEqual(updated.pk, existing.pk)
        self.assertTrue(updated.fixed_in_core)  # preservado
        self.assertTrue(updated.fixed_in_upload)  # setado agora
        self.assertEqual(updated.updated_by, self.user)


class FixPidV2GetOrCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fixpid-goc", password="x")
        self.ppx = PidProviderXML.objects.create(creator=self.user, v3="ABC", v2="V2-OLD")

    def test_returns_existing_without_creating_new(self):
        existing = FixPidV2.create(
            self.user, self.ppx, incorrect_pid_v2="V2-OLD", correct_pid_v2="V2-NEW"
        )

        found = FixPidV2.get_or_create(self.user, self.ppx, correct_pid_v2="V2-OTHER")

        self.assertEqual(found.pk, existing.pk)
        self.assertEqual(FixPidV2.objects.count(), 1)

    def test_creates_using_pid_provider_xml_v2_as_incorrect(self):
        obj = FixPidV2.get_or_create(self.user, self.ppx, correct_pid_v2="V2-NEW")

        self.assertEqual(obj.incorrect_pid_v2, "V2-OLD")
        self.assertEqual(obj.correct_pid_v2, "V2-NEW")
