from unittest.mock import patch

from django.test import SimpleTestCase

from pid_provider.models import PidProviderXMLRegistration, XMLVersion


class XMLVersionTests(SimpleTestCase):
    def test_string_representation_without_pid_provider_xml(self):
        xml_version = XMLVersion(pid_provider_xml=None)

        self.assertEqual(str(xml_version), "- None")


class PidProviderXMLRegistrationTests(SimpleTestCase):
    @patch.object(PidProviderXMLRegistration, "save")
    def test_skipped_event_does_not_store_detail(self, save):
        registration = PidProviderXMLRegistration.record(
            user=None,
            event_status=PidProviderXMLRegistration.EVENT_SKIPPED,
            detail={"large": "payload"},
        )

        save.assert_called_once_with()
        self.assertIsNotNone(registration)
        self.assertIsNone(registration.detail)
