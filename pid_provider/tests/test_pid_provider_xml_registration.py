"""
Testes para PidProviderXMLRegistration (pid_provider/models.py).

O caso "skipped não grava detail" já está coberto em test_models.py; aqui
cobrimos _serialize_detail isoladamente e os demais status (que DEVEM
gravar detail), incluindo a substituição de detail["registered"] (um
objeto PidProviderXML) por {"id", "v3"} para permitir serialização JSON.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from pid_provider.models import PidProviderXML, PidProviderXMLRegistration

User = get_user_model()


class SerializeDetailTests(TestCase):
    def test_returns_none_for_falsy_detail(self):
        self.assertIsNone(PidProviderXMLRegistration._serialize_detail(None))
        self.assertIsNone(PidProviderXMLRegistration._serialize_detail({}))

    def test_replaces_registered_object_with_id_and_v3(self):
        user = User.objects.create_user(username="serialize-user", password="x")
        ppx = PidProviderXML.objects.create(creator=user, v3="V3-123")

        result = PidProviderXMLRegistration._serialize_detail(
            {"registered": ppx, "other": "value"}
        )

        self.assertEqual(result["registered"], {"id": ppx.id, "v3": "V3-123"})
        self.assertEqual(result["other"], "value")

    def test_keeps_registered_untouched_when_not_a_model_instance(self):
        result = PidProviderXMLRegistration._serialize_detail({"registered": None})
        self.assertIsNone(result["registered"])

    def test_does_not_mutate_original_dict(self):
        user = User.objects.create_user(username="serialize-user2", password="x")
        ppx = PidProviderXML.objects.create(creator=user, v3="V3-456")
        original = {"registered": ppx}

        PidProviderXMLRegistration._serialize_detail(original)

        self.assertIs(original["registered"], ppx)


class RecordTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="record-user", password="x")

    def test_lightweight_statuses_do_not_store_detail(self):
        for status in PidProviderXMLRegistration.LIGHTWEIGHT_STATUSES:
            registration = PidProviderXMLRegistration.record(
                user=self.user, event_status=status, detail={"payload": "x"}
            )
            self.assertIsNone(registration.detail)
            self.assertEqual(registration.event_status, status)

    def test_non_lightweight_status_stores_serialized_detail(self):
        registration = PidProviderXMLRegistration.record(
            user=self.user,
            event_status=PidProviderXMLRegistration.EVENT_CONFLICT,
            detail={"error_msg": "conflict!"},
        )
        self.assertEqual(registration.detail, {"error_msg": "conflict!"})

    def test_pkg_name_falls_back_to_pid_provider_xml_pkg_name(self):
        ppx = PidProviderXML.objects.create(
            creator=self.user, v3="V3-789", pkg_name="pkg-from-ppx"
        )

        registration = PidProviderXMLRegistration.record(
            user=self.user,
            event_status=PidProviderXMLRegistration.EVENT_UNMATCHED,
            pid_provider_xml=ppx,
        )

        self.assertEqual(registration.pkg_name, "pkg-from-ppx")

    def test_explicit_pkg_name_overrides_pid_provider_xml_pkg_name(self):
        ppx = PidProviderXML.objects.create(
            creator=self.user, v3="V3-999", pkg_name="pkg-from-ppx"
        )

        registration = PidProviderXMLRegistration.record(
            user=self.user,
            event_status=PidProviderXMLRegistration.EVENT_ERROR,
            pid_provider_xml=ppx,
            pkg_name="pkg-explicit",
        )

        self.assertEqual(registration.pkg_name, "pkg-explicit")

    def test_str_representation(self):
        registration = PidProviderXMLRegistration.record(
            user=self.user,
            event_status=PidProviderXMLRegistration.EVENT_ERROR,
            pkg_name="pkg-str",
        )
        self.assertIn("pkg-str", str(registration))
        self.assertIn("error", str(registration))
