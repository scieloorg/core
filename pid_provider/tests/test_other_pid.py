"""Testes para OtherPid (pid_provider/models.py)."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from pid_provider.models import OtherPid, PidProviderXML, XMLVersion

User = get_user_model()


class OtherPidGetOrCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="otherpid-user", password="x")
        self.ppx = PidProviderXML.objects.create(creator=self.user, v3="ABC")
        # version é obrigatório (truthy) para get_or_create -- um FK vazio
        # (None) faz a validação falhar e levantar ValueError.
        self.version = XMLVersion.objects.create(creator=self.user, pid_provider_xml=self.ppx)

    def test_raises_value_error_when_any_required_argument_is_missing(self):
        with self.assertRaises(ValueError):
            OtherPid.get_or_create(
                pid_type=None,
                pid_in_xml="OLD-V3",
                version=self.version,
                user=self.user,
                pid_provider_xml=self.ppx,
            )

    def test_raises_value_error_when_version_is_missing(self):
        with self.assertRaises(ValueError):
            OtherPid.get_or_create(
                pid_type="pid_v3",
                pid_in_xml="OLD-V3",
                version=None,
                user=self.user,
                pid_provider_xml=self.ppx,
            )

    def test_creates_new_when_none_exists(self):
        obj = OtherPid.get_or_create(
            pid_type="pid_v3",
            pid_in_xml="OLD-V3",
            version=self.version,
            user=self.user,
            pid_provider_xml=self.ppx,
        )

        self.assertIsNotNone(obj.pk)
        self.assertEqual(obj.pid_type, "pid_v3")
        self.assertEqual(obj.pid_in_xml, "OLD-V3")
        self.assertEqual(obj.creator, self.user)
        self.assertEqual(obj.pid_provider_xml, self.ppx)

    def test_returns_existing_without_duplicating(self):
        first = OtherPid.get_or_create(
            pid_type="pid_v2",
            pid_in_xml="OLD-V2",
            version=self.version,
            user=self.user,
            pid_provider_xml=self.ppx,
        )

        second = OtherPid.get_or_create(
            pid_type="pid_v2",
            pid_in_xml="OLD-V2",
            version=self.version,
            user=self.user,
            pid_provider_xml=self.ppx,
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(OtherPid.objects.filter(pid_provider_xml=self.ppx).count(), 1)

    def test_created_updated_prefers_updated_when_present(self):
        obj = OtherPid.get_or_create(
            pid_type="pid_v3",
            pid_in_xml="OLD-V3",
            version=self.version,
            user=self.user,
            pid_provider_xml=self.ppx,
        )
        obj.updated = None
        self.assertEqual(obj.created_updated, obj.created)
