from unittest.mock import MagicMock, patch

from django.test import TestCase
from lxml import etree as ET

from doi_manager.crossmark import (
    CROSSREF_DEPOSIT_URL,
    CROSSREF_TEST_DEPOSIT_URL,
    build_crossmark_policy_page_xml,
    deposit_crossmark_policy_page,
)


class BuildCrossmarkPolicyPageXMLTest(TestCase):
    def _parse(self, xml_str):
        return ET.fromstring(xml_str.encode("utf-8"))

    def _make_xml(self, **kwargs):
        defaults = dict(
            doi="10.1234/update-policy",
            url="https://example.org/update-policy",
            depositor_name="Test Depositor",
            depositor_email_address="depositor@example.org",
            registrant="Test Registrant",
        )
        defaults.update(kwargs)
        return build_crossmark_policy_page_xml(**defaults)

    def test_returns_string(self):
        xml = self._make_xml()
        self.assertIsInstance(xml, str)

    def test_xml_declaration_present(self):
        xml = self._make_xml()
        self.assertIn("<?xml", xml)

    def test_doi_batch_root_element(self):
        xml = self._make_xml()
        root = self._parse(xml)
        self.assertIn("doi_batch", root.tag)

    def test_schema_version(self):
        xml = self._make_xml()
        root = self._parse(xml)
        self.assertEqual(root.get("version"), "4.4.0")

    def test_doi_batch_id_present(self):
        xml = self._make_xml()
        root = self._parse(xml)
        ns = "http://www.crossref.org/schema/4.4.0"
        doi_batch_id = root.find(f".//{{{ns}}}doi_batch_id")
        self.assertIsNotNone(doi_batch_id)
        self.assertTrue(doi_batch_id.text)

    def test_timestamp_present(self):
        xml = self._make_xml()
        root = self._parse(xml)
        ns = "http://www.crossref.org/schema/4.4.0"
        timestamp = root.find(f".//{{{ns}}}timestamp")
        self.assertIsNotNone(timestamp)
        self.assertTrue(timestamp.text)

    def test_depositor_name(self):
        xml = self._make_xml(depositor_name="My Depositor")
        root = self._parse(xml)
        ns = "http://www.crossref.org/schema/4.4.0"
        depositor_name = root.find(f".//{{{ns}}}depositor_name")
        self.assertIsNotNone(depositor_name)
        self.assertEqual(depositor_name.text, "My Depositor")

    def test_depositor_email_address(self):
        xml = self._make_xml(depositor_email_address="test@scielo.org")
        root = self._parse(xml)
        ns = "http://www.crossref.org/schema/4.4.0"
        email = root.find(f".//{{{ns}}}email_address")
        self.assertIsNotNone(email)
        self.assertEqual(email.text, "test@scielo.org")

    def test_registrant(self):
        xml = self._make_xml(registrant="SciELO")
        root = self._parse(xml)
        ns = "http://www.crossref.org/schema/4.4.0"
        registrant = root.find(f".//{{{ns}}}registrant")
        self.assertIsNotNone(registrant)
        self.assertEqual(registrant.text, "SciELO")

    def test_doi_in_doi_data(self):
        xml = self._make_xml(doi="10.5678/my-policy")
        root = self._parse(xml)
        ns = "http://www.crossref.org/schema/4.4.0"
        doi_el = root.find(f".//{{{ns}}}doi_data/{{{ns}}}doi")
        self.assertIsNotNone(doi_el)
        self.assertEqual(doi_el.text, "10.5678/my-policy")

    def test_url_in_doi_data(self):
        xml = self._make_xml(url="https://scielo.org/policy")
        root = self._parse(xml)
        ns = "http://www.crossref.org/schema/4.4.0"
        resource_el = root.find(f".//{{{ns}}}doi_data/{{{ns}}}resource")
        self.assertIsNotNone(resource_el)
        self.assertEqual(resource_el.text, "https://scielo.org/policy")

    def test_database_element_present(self):
        xml = self._make_xml()
        root = self._parse(xml)
        ns = "http://www.crossref.org/schema/4.4.0"
        database = root.find(f".//{{{ns}}}database")
        self.assertIsNotNone(database)

    def test_dataset_element_present(self):
        xml = self._make_xml()
        root = self._parse(xml)
        ns = "http://www.crossref.org/schema/4.4.0"
        dataset = root.find(f".//{{{ns}}}dataset")
        self.assertIsNotNone(dataset)
        self.assertEqual(dataset.get("dataset_type"), "record")


class DepositCrossmarkPolicyPageTest(TestCase):
    def _call(self, **kwargs):
        defaults = dict(
            doi="10.1234/update-policy",
            url="https://example.org/update-policy",
            login_id="mylogin",
            login_passwd="mypassword",
            depositor_name="Test Depositor",
            depositor_email_address="depositor@example.org",
            registrant="Test Registrant",
        )
        defaults.update(kwargs)
        return deposit_crossmark_policy_page(**defaults)

    def test_raises_value_error_when_doi_is_missing(self):
        with self.assertRaises(ValueError):
            self._call(doi=None)

    def test_raises_value_error_when_doi_is_empty(self):
        with self.assertRaises(ValueError):
            self._call(doi="")

    def test_raises_value_error_when_url_is_missing(self):
        with self.assertRaises(ValueError):
            self._call(url=None)

    def test_raises_value_error_when_url_is_empty(self):
        with self.assertRaises(ValueError):
            self._call(url="")

    def test_raises_value_error_when_login_id_is_missing(self):
        with self.assertRaises(ValueError):
            self._call(login_id=None)

    def test_raises_value_error_when_login_id_is_empty(self):
        with self.assertRaises(ValueError):
            self._call(login_id="")

    def test_raises_value_error_when_login_passwd_is_missing(self):
        with self.assertRaises(ValueError):
            self._call(login_passwd=None)

    def test_raises_value_error_when_login_passwd_is_empty(self):
        with self.assertRaises(ValueError):
            self._call(login_passwd="")

    @patch("doi_manager.crossmark.requests.post")
    def test_posts_to_production_url_by_default(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self._call()

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], CROSSREF_DEPOSIT_URL)

    @patch("doi_manager.crossmark.requests.post")
    def test_posts_to_test_url_when_is_test_is_true(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self._call(is_test=True)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], CROSSREF_TEST_DEPOSIT_URL)

    @patch("doi_manager.crossmark.requests.post")
    def test_sends_operation_doMDUpload(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self._call()

        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["data"]["operation"], "doMDUpload")

    @patch("doi_manager.crossmark.requests.post")
    def test_sends_login_credentials(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self._call(login_id="testuser", login_passwd="testpass")

        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["data"]["login_id"], "testuser")
        self.assertEqual(call_kwargs["data"]["login_passwd"], "testpass")

    @patch("doi_manager.crossmark.requests.post")
    def test_sends_xml_file_as_multipart(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self._call(doi="10.1234/policy")

        call_kwargs = mock_post.call_args[1]
        self.assertIn("fname", call_kwargs["files"])
        fname_tuple = call_kwargs["files"]["fname"]
        # fname_tuple is (filename, content, mimetype)
        self.assertIn("10.1234_policy", fname_tuple[0])
        self.assertEqual(fname_tuple[2], "text/xml")

    @patch("doi_manager.crossmark.requests.post")
    def test_returns_response(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self._call()

        self.assertIs(result, mock_response)

    @patch("doi_manager.crossmark.requests.post")
    def test_raises_http_error_on_bad_status(self, mock_post):
        from requests import HTTPError

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_post.return_value = mock_response

        with self.assertRaises(HTTPError):
            self._call()
