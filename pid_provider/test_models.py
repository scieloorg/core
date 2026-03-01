import logging
from datetime import datetime
from unittest import mock
from unittest.mock import ANY, MagicMock, Mock, call, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from lxml import etree
from xmlsps.xml_sps_lib import XMLWithPre

from pid_provider import exceptions, models
from pid_provider.xml_sps_adapter import PidProviderXMLAdapter

User = get_user_model()


def _get_xml_adapter_from_file(path):
    for xml_with_pre in XMLWithPre.create(path=path):
        obj = PidProviderXMLAdapter(xml_with_pre)
        return obj


def _get_xml_with_pre(xml=None):
    xml = xml or "<article/>"
    return XMLWithPre("", etree.fromstring(xml))


def _get_xml_adapter(xml=None):
    xml = xml or "<article/>"
    xml_with_pre = XMLWithPre("", etree.fromstring(xml))
    obj = PidProviderXMLAdapter(xml_with_pre)
    return obj


def _get_xml_adapter_with_issue_data():
    xml_adapter = _get_xml_adapter()
    xml_adapter.journal_issn_electronic = "data-issn-e"
    xml_adapter.journal_issn_print = "data-issn-p"
    xml_adapter.volume = "data-vol"
    xml_adapter.number = "data-num"
    xml_adapter.suppl = "data-suppl"
    xml_adapter.pub_year = "data-year"
    xml_adapter.issue = models.XMLIssue.get_or_create(
        models.XMLJournal.get_or_create("data-issn-e", "data-issn-p"),
        "data-vol",
        "data-num",
        "data-suppl",
        "data-year",
    )
    xml_adapter.fpage = "data-fpage"
    xml_adapter.fpage_seq = "data-fpage-seq"
    xml_adapter.lpage = "data-lpage"

    xml_adapter.article_pub_year = "data-pub-year"
    xml_adapter.v3 = "123456789012345678901v3"
    xml_adapter.v2 = "123456789012345678901v2"
    xml_adapter.aop_pid = "12345678901234567890aop"

    xml_adapter.main_doi = "data-main_doi"
    xml_adapter.elocation_id = "data-elocation_id"
    return xml_adapter


class PidProviderXMLValidateQueryParamsTest(TestCase):
    def setUp(self):
        self.article_params = {
            "z_collab": "VALUE",
            "z_links": "Links",
            "z_partial_body": "Body",
            "z_surnames": "Z_SURNAMES",
            "article_pub_year": "2020",
            "elocation_id": "e19347",
            "journal__issn_electronic": "issn electronic",
            "journal__issn_print": "issn print",
            "main_doi": "DOI",
            "pkg_name": "pkgName",
        }

        self.issue_params = {
            "issue__pub_year": "year",
            "issue__volume": "vol",
            "issue__number": "num",
            "issue__suppl": "suppl",
            "fpage": "1",
            "fpage_seq": "a",
            "lpage": "11",
        }

    def test_validate_query_params_all_present(self):
        params = self.article_params
        result = models.PidProviderXML.validate_query_params(params)
        self.assertTrue(result)

    def test_validate_query_params_all_present_plus_issue_params(self):
        params = self.article_params
        params.update(self.issue_params)
        result = models.PidProviderXML.validate_query_params(params)
        self.assertTrue(result)

    def test_validate_query_params_issue_params_only(self):
        params = {}
        params.update(self.issue_params)
        with self.assertRaises(exceptions.NotEnoughParametersToGetDocumentRecordError):
            result = models.PidProviderXML.validate_query_params(params)

    def test_validate_query_params_journal_issns_absence(self):
        params = self.article_params
        params.update(self.issue_params)
        del params["journal__issn_print"]
        del params["journal__issn_electronic"]
        with self.assertRaises(exceptions.NotEnoughParametersToGetDocumentRecordError):
            result = models.PidProviderXML.validate_query_params(params)

    def test_validate_query_params_pub_year_absence(self):
        params = self.article_params
        params.update(self.issue_params)
        del params["article_pub_year"]
        del params["issue__pub_year"]
        with self.assertRaises(exceptions.NotEnoughParametersToGetDocumentRecordError):
            result = models.PidProviderXML.validate_query_params(params)

    def test_validate_query_params_main_doi_absence(self):
        params = self.article_params
        params.update(self.issue_params)
        del params["main_doi"]
        result = models.PidProviderXML.validate_query_params(params)
        self.assertTrue(result)

    def test_validate_query_params_fpage_absence(self):
        params = self.article_params
        params.update(self.issue_params)
        del params["fpage"]
        result = models.PidProviderXML.validate_query_params(params)
        self.assertTrue(result)

    def test_validate_query_params_elocation_id_absence(self):
        params = self.article_params
        params.update(self.issue_params)
        del params["elocation_id"]
        result = models.PidProviderXML.validate_query_params(params)
        self.assertTrue(result)

    def test_validate_query_params_main_doi_fpage_elocation_id_absence(self):
        params = self.article_params
        params.update(self.issue_params)
        del params["main_doi"]
        del params["fpage"]
        del params["elocation_id"]
        result = models.PidProviderXML.validate_query_params(params)
        self.assertTrue(result)

    def test_validate_query_params_z_surnames_id_absence(self):
        params = self.article_params
        params.update(self.issue_params)
        del params["main_doi"]
        del params["fpage"]
        del params["elocation_id"]
        del params["z_surnames"]
        result = models.PidProviderXML.validate_query_params(params)
        self.assertTrue(result)

    def test_validate_query_params_z_collab_id_absence(self):
        params = self.article_params
        params.update(self.issue_params)
        del params["main_doi"]
        del params["fpage"]
        del params["elocation_id"]
        del params["z_collab"]
        result = models.PidProviderXML.validate_query_params(params)
        self.assertTrue(result)

    def test_validate_query_params_z_collab_id_absence(self):
        params = self.article_params
        params.update(self.issue_params)
        del params["main_doi"]
        del params["fpage"]
        del params["elocation_id"]
        del params["z_links"]
        result = models.PidProviderXML.validate_query_params(params)
        self.assertTrue(result)

    def test_validate_query_params_z_collab_id_absence(self):
        params = self.article_params
        params.update(self.issue_params)
        del params["main_doi"]
        del params["fpage"]
        del params["elocation_id"]
        del params["pkg_name"]
        result = models.PidProviderXML.validate_query_params(params)
        self.assertTrue(result)

    def test_validate_query_params_z_collab_id_absence(self):
        params = self.article_params
        params.update(self.issue_params)
        del params["main_doi"]
        del params["fpage"]
        del params["elocation_id"]
        del params["pkg_name"]
        del params["z_surnames"]
        del params["z_collab"]
        del params["z_links"]

        with self.assertRaises(exceptions.NotEnoughParametersToGetDocumentRecordError):
            result = models.PidProviderXML.validate_query_params(params)


@patch(
    "pid_provider.xml_sps_adapter.PidProviderXMLAdapter.query_list",
    new_callable=mock.PropertyMock,
)
@patch(
    "pid_provider.models.PidProviderXML.validate_query_params",
    return_value=True,
)
@patch("pid_provider.models.PidProviderXML.objects.get")
class PidProviderXMLQueryDocumentTest(TestCase):
    def test_query_document_is_called_with_query_params(
        self,
        mock_get,
        mock_validate_params,
        mock_query_list,
    ):
        """
        PidProviderXML._query_document is called with parameters returned by
        PidProviderXML.query_list
        """
        params_list = [
            {"key": "value"},
        ]
        mock_query_list.return_value = params_list
        mock_get.side_effect = models.PidProviderXML.DoesNotExist
        xml_adapter = _get_xml_adapter()
        result = models.PidProviderXML._query_document(xml_adapter)
        mock_get.assert_called_once_with(**{"key": "value"})

    def test_query_document_returns_none_if_document_does_not_exist(
        self,
        mock_get,
        mock_validate_params,
        mock_query_list,
    ):
        params_list = [
            {"key": "value"},
        ]
        mock_query_list.return_value = params_list
        mock_get.side_effect = models.PidProviderXML.DoesNotExist
        xml_adapter = _get_xml_adapter()
        result = models.PidProviderXML._query_document(xml_adapter)
        self.assertIsNone(result)

    def test_query_document_returns_found_document(
        self,
        mock_get,
        mock_validate_params,
        mock_query_list,
    ):
        params_list = [
            {"key": "value"},
        ]
        mock_query_list.return_value = params_list
        mock_get.return_value = models.PidProviderXML()
        xml_adapter = _get_xml_adapter()
        result = models.PidProviderXML._query_document(xml_adapter)
        self.assertEqual(models.PidProviderXML, type(result))

    def test_query_document_returns_found_item_at_the_second_round(
        self,
        mock_get,
        mock_validate_params,
        mock_query_list,
    ):
        params_list = [
            {"key": "value"},
            {"key": "value2"},
        ]
        mock_query_list.return_value = params_list
        mock_get.side_effect = [
            models.PidProviderXML.DoesNotExist,
            models.PidProviderXML(),
        ]
        xml_adapter = _get_xml_adapter()
        result = models.PidProviderXML._query_document(xml_adapter)
        self.assertEqual(models.PidProviderXML, type(result))

    def test_query_document_raises_query_document_error_because_multiple_objects_returned(
        self,
        mock_get,
        mock_validate_params,
        mock_query_list,
    ):
        params_list = [
            {"key": "value"},
        ]
        mock_query_list.return_value = params_list
        mock_get.side_effect = models.PidProviderXML.MultipleObjectsReturned
        with self.assertRaises(
            exceptions.QueryDocumentMultipleObjectsReturnedError
        ) as exc:
            xml_adapter = _get_xml_adapter()
            result = models.PidProviderXML._query_document(xml_adapter)

    def test_query_document_raises_error(
        self,
        mock_get,
        mock_validate_params,
        mock_query_list,
    ):
        """
        PidProviderXML._query_document is called with parameters returned by
        PidProviderXML.query_list
        """
        params_list = [
            {"key": "value"},
        ]
        mock_query_list.return_value = params_list
        mock_validate_params.side_effect = (
            exceptions.NotEnoughParametersToGetDocumentRecordError
        )

        with self.assertRaises(exceptions.NotEnoughParametersToGetDocumentRecordError):
            xml_adapter = _get_xml_adapter()
            result = models.PidProviderXML._query_document(xml_adapter)


@patch("pid_provider.models.PidProviderXML._query_document")
class PidProviderXMLGetRegisteredTest(TestCase):
    def setUp(self):
        self.xml_with_pre = _get_xml_with_pre()

    def test_get_registered_returns_dict_with_registered_data(
        self,
        mock_query_document,
    ):
        pid_req_xml = models.PidProviderXML()
        pid_req_xml.pkg_name = "registered_pkg_name"
        pid_req_xml.v2 = "registered_v2"
        pid_req_xml.v3 = "registered_v3"
        pid_req_xml.aop_pid = "registered_aop_pid"
        pid_req_xml.created = datetime(2023, 2, 20)
        pid_req_xml.updated = datetime(2023, 2, 20)

        mock_query_document.return_value = pid_req_xml

        result = models.PidProviderXML.get_registered(self.xml_with_pre)
        expected = {
            "v3": "registered_v3",
            "v2": "registered_v2",
            "aop_pid": "registered_aop_pid",
            "pkg_name": "registered_pkg_name",
            "created": "2023-02-20T00:00:00",
            "updated": "2023-02-20T00:00:00",
            "record_status": "updated",
        }
        self.assertDictEqual(expected, result)

    def test_get_registered_returns_none(
        self,
        mock_query_document,
    ):
        mock_query_document.return_value = None

        result = models.PidProviderXML.get_registered(self.xml_with_pre)
        self.assertIsNone(result)

    def test_get_registered_returns_error_multiple_return(
        self,
        mock_query_document,
    ):
        mock_query_document.side_effect = (
            exceptions.QueryDocumentMultipleObjectsReturnedError
        )

        result = models.PidProviderXML.get_registered(self.xml_with_pre)
        self.assertIn("error_type", result.keys())
        self.assertIn("error_msg", result.keys())

    def test_get_registered_returns_error_not_enough_params(
        self,
        mock_query_document,
    ):
        mock_query_document.side_effect = (
            exceptions.NotEnoughParametersToGetDocumentRecordError
        )

        result = models.PidProviderXML.get_registered(self.xml_with_pre)
        self.assertIn("error_type", result.keys())
        self.assertIn("error_msg", result.keys())


class PidProviderXMLEvaluateRegistrationTest(TestCase):
    def setUp(self):
        self.xml_adapter = _get_xml_adapter()

    def test_evaluate_registration_accepts_xml_is_aop_and_registered_is_aop(self):
        registered = Mock(spec=models.PidProviderXML)
        registered.is_aop = True

        self.xml_adapter.is_aop = True

        result = models.PidProviderXML.evaluate_registration(
            self.xml_adapter, registered
        )
        self.assertTrue(result)

    def test_evaluate_registration_accepts_xml_is_not_aop_and_registered_is_aop(self):
        registered = Mock(spec=models.PidProviderXML)
        registered.is_aop = True

        self.xml_adapter.is_aop = False

        result = models.PidProviderXML.evaluate_registration(
            self.xml_adapter, registered
        )
        self.assertTrue(result)

    def test_evaluate_registration_raises_error(self):
        registered = Mock(spec=models.PidProviderXML)
        registered.is_aop = False

        self.xml_adapter.is_aop = True

        with self.assertRaises(exceptions.ForbiddenPidProviderXMLRegistrationError):
            result = models.PidProviderXML.evaluate_registration(
                self.xml_adapter, registered
            )


@patch("pid_provider.models.PidProviderXML._get_unique_v2")
class PidProviderXMLAddV2Test(TestCase):
    def _get_xml_adapter(self, v2=None, v3=None, aop_pid=None):
        v2 = (
            v2
            and f'<article-id specific-use="scielo-v2" pub-id-type="publisher-id">{v2}</article-id>'
            or ""
        )
        v3 = (
            v3
            and f'<article-id specific-use="scielo-v3" pub-id-type="publisher-id">{v3}</article-id>'
            or ""
        )
        aop_pid = (
            aop_pid
            and f'<article-id specific-use="previous-pid" pub-id-type="publisher-id">{aop_pid}</article-id>'
            or ""
        )

        return _get_xml_adapter(
            f"""<article>
            <front><article-meta>
            {v2}
            {v3}
            {aop_pid}
            <article-id pub-id-type="doi">10.36416/1806-3756/e20220072</article-id>
            <article-id pub-id-type="other">01100</article-id>
            </article-meta></front>
            </article>"""
        )

    # TODO
    # def test_add_pid_v2_uses_registered_pid_v2(
    #     self,
    #     mock_get_unique_v2,
    # ):
    #     found = models.PidProviderXML()
    #     found.v2 = "registered_v2"

    #     xml_adapter = self._get_xml_adapter(v2='xml_v2')

    #     mock_get_unique_v2.return_value = "generated_v2"

    #     models.PidProviderXML._add_pid_v2(xml_adapter, found)
    #     self.assertEqual("registered_v2", xml_adapter.v2)

    def test_add_pid_v2_replace_xml_v2_because_its_value_is_invalid_length_is_not_23(
        self,
        mock_get_unique_v2,
    ):
        found = models.PidProviderXML()
        found.v2 = None

        xml_adapter = self._get_xml_adapter(v2="bad_size_not_23")

        mock_get_unique_v2.return_value = "S1806-37132022000201100"

        models.PidProviderXML._add_pid_v2(xml_adapter, found)
        self.assertEqual("S1806-37132022000201100", xml_adapter.v2)

    def test_add_pid_v2_keeps_xml_v2(
        self,
        mock_get_unique_v2,
    ):
        found = models.PidProviderXML()
        found.v2 = None

        xml_adapter = self._get_xml_adapter(v2="S1806-37132022000199999")

        mock_get_unique_v2.return_value = "S1806-37132022000300001"

        models.PidProviderXML._add_pid_v2(xml_adapter, found)
        self.assertEqual("S1806-37132022000199999", xml_adapter.v2)

    def test_add_pid_v2_uses_unique_v2(
        self,
        mock_get_unique_v2,
    ):
        found = models.PidProviderXML()
        found.v2 = None

        xml_adapter = self._get_xml_adapter()

        mock_get_unique_v2.return_value = "S1806-37132022000201100"

        models.PidProviderXML._add_pid_v2(xml_adapter, found)
        self.assertEqual("S1806-37132022000201100", xml_adapter.v2)


class PidProviderXMLAddAopPidTest(TestCase):
    def _get_xml_adapter(self, v2=None, v3=None, aop_pid=None):
        v2 = (
            v2
            and f'<article-id specific-use="scielo-v2" pub-id-type="publisher-id">{v2}</article-id>'
            or ""
        )
        v3 = (
            v3
            and f'<article-id specific-use="scielo-v3" pub-id-type="publisher-id">{v3}</article-id>'
            or ""
        )
        aop_pid = (
            aop_pid
            and f'<article-id specific-use="previous-pid" pub-id-type="publisher-id">{aop_pid}</article-id>'
            or ""
        )

        return _get_xml_adapter(
            f"""<article>
            <front><article-meta>
            {v2}
            {v3}
            {aop_pid}
            <article-id pub-id-type="doi">10.36416/1806-3756/e20220072</article-id>
            <article-id pub-id-type="other">01100</article-id>
            </article-meta></front>
            </article>"""
        )

    def test_add_aop_pid_uses_registered_aop_pid(
        self,
    ):
        found = models.PidProviderXML()
        found.aop_pid = "12345678901234567890aop"

        xml_adapter = self._get_xml_adapter(aop_pid="xml_aop_pid")

        models.PidProviderXML._add_aop_pid(xml_adapter, found)
        self.assertEqual("12345678901234567890aop", xml_adapter.aop_pid)

    def test_add_aop_pid_does_not_replace_by_none(
        self,
    ):
        found = models.PidProviderXML()
        found.aop_pid = None

        xml_adapter = self._get_xml_adapter(aop_pid="xml_aop_pid")

        models.PidProviderXML._add_aop_pid(xml_adapter, found)
        self.assertEqual("xml_aop_pid", xml_adapter.aop_pid)


@patch("pid_provider.models.PidProviderXML._is_registered_pid")
@patch("pid_provider.models.PidProviderXML._get_unique_v3")
class PidProviderXMLAddPidV3Test(TestCase):
    def _get_xml_adapter(self, v2=None, v3=None, aop_pid=None):
        v2 = (
            v2
            and f'<article-id specific-use="scielo-v2" pub-id-type="publisher-id">{v2}</article-id>'
            or ""
        )
        v3 = (
            v3
            and f'<article-id specific-use="scielo-v3" pub-id-type="publisher-id">{v3}</article-id>'
            or ""
        )
        aop_pid = (
            aop_pid
            and f'<article-id specific-use="previous-pid" pub-id-type="publisher-id">{aop_pid}</article-id>'
            or ""
        )

        return _get_xml_adapter(
            f"""<article>
            <front><article-meta>
            {v2}
            {v3}
            {aop_pid}
            <article-id pub-id-type="doi">10.36416/1806-3756/e20220072</article-id>
            <article-id pub-id-type="other">01100</article-id>
            </article-meta></front>
            </article>"""
        )

    def test_add_pid_v3_uses_registered_v3(
        self,
        mock__get_unique_v3,
        mock__is_registered_pid,
    ):
        found = models.PidProviderXML()
        found.v3 = "123456789012345678901v3"

        xml_adapter = self._get_xml_adapter(v3="xml_v3")

        models.PidProviderXML._add_pid_v3(xml_adapter, found)
        self.assertEqual("123456789012345678901v3", xml_adapter.v3)

    def test_add_pid_v3_replaced_by_generated(
        self,
        mock__get_unique_v3,
        mock__is_registered_pid,
    ):
        mock__is_registered_pid.return_value = True
        mock__get_unique_v3.return_value = "gen456789012345678901v3"

        found = None

        xml_adapter = self._get_xml_adapter(v3="xml_v3")

        models.PidProviderXML._add_pid_v3(xml_adapter, found)
        self.assertEqual("gen456789012345678901v3", xml_adapter.v3)

    def test_add_pid_v3_keeps_xml_v3(
        self,
        mock__get_unique_v3,
        mock__is_registered_pid,
    ):
        mock__is_registered_pid.return_value = False
        mock__get_unique_v3.return_value = "gen456789012345678901v3"

        found = None

        xml_adapter = self._get_xml_adapter(v3="xml456789012345678901v3")

        models.PidProviderXML._add_pid_v3(xml_adapter, found)
        self.assertEqual("xml456789012345678901v3", xml_adapter.v3)


class PidProviderXMLIsEqualToTest(TestCase):
    def test_is_equal_to_returns_false(self):
        xml_adapter = _get_xml_adapter_from_file(
            "./pid_provider/fixtures/article/ex-aop.xml"
        )
        registered = models.PidProviderXML()

        result = registered.is_equal_to(xml_adapter)
        self.assertFalse(result)


class PidProviderXMLAddDataForRegularArticleTest(TestCase):
    def setUp(self):
        user = User()
        xml_adapter = _get_xml_adapter_from_file(
            "./pid_provider/fixtures/article/ex-aop.xml"
        )
        self.registered = models.PidProviderXML()
        self.registered._add_data(xml_adapter, user)

    def test_v3(self):
        self.assertEqual("yH6CLqxFJsQKrHj7zXkwL3G", self.registered.v3)

    def test_v2(self):
        self.assertEqual("S1413-41522020000400627", self.registered.v2)

    def test_aop_pid(self):
        self.assertEqual("S1413-41522020005000111", self.registered.aop_pid)

    def test_main_doi(self):
        self.assertEqual("10.1590/S1413-4152202020180029", self.registered.main_doi)

    def test_fpage(self):
        self.assertEqual("627", self.registered.fpage)

    def test_fpage_seq(self):
        self.assertEqual(None, self.registered.fpage_seq)

    def test_lpage(self):
        self.assertEqual("634", self.registered.lpage)

    def test_elocation_id(self):
        self.assertEqual(None, self.registered.elocation_id)

    def test_article_pub_year(self):
        self.assertEqual("2020", self.registered.article_pub_year)

    def test_z_surnames(self):
        self.assertEqual(
            "544700df348a47fdd7c55713054e12663a0c530e60e7a166395a496f77de9d36",
            self.registered.z_surnames,
        )

    def test_z_collab(self):
        self.assertIsNone(self.registered.z_collab)

    def test_z_links(self):
        self.assertIsNone(self.registered.z_links)

    def test_z_partial_body(self):
        self.assertEqual(
            "2e07675bfe91c65e1544ada450ff2e956fef9b492d30e997ebd47687e0f7afa2",
            self.registered.z_partial_body,
        )


@patch(
    "pid_provider.models.utcnow",
    side_effect=[datetime(2020, 2, 2, 0, 0), datetime(2020, 2, 3, 0, 0)],
)
@patch("pid_provider.models.XMLVersion.save_file")
@patch("pid_provider.models.XMLVersion.save")
@patch("pid_provider.models.XMLIssue.save")
@patch("pid_provider.models.XMLJournal.save")
@patch("pid_provider.models.PidProviderXML.save")
@patch("pid_provider.models.PidRequest.save")
class PidProviderXMLRegisterTest(TestCase):
    def test_register_returns_error(
        self,
        mock_pid_request_save,
        mock_pid_provider_xml_save,
        mock_xml_journal_save,
        mock_xml_issue_save,
        mock_xml_version_save,
        mock_xml_version_save_file,
        mock_now,
    ):
        expected = {
            "result_type": "<class 'pid_provider.exceptions.NotEnoughParametersToGetDocumentRecordError'>",
            "result_message": "No attribute enough for disambiguations {'z_surnames': None, 'z_collab': None, 'main_doi': None, 'z_links': None, 'z_partial_body': None, 'pkg_name': None, 'elocation_id': None, 'journal__issn_print': None, 'journal__issn_electronic': None, 'article_pub_year': None}",
            "origin": "filename.xml",
            "xml": "<article/>",
        }

        user = User()
        xml_with_pre = _get_xml_with_pre()
        result = models.PidProviderXML.register(
            xml_with_pre=xml_with_pre,
            filename="filename.xml",
            user=user,
        )
        print(result)
        self.assertEqual(expected["result_type"], result["result_type"])
        self.assertIsNotNone(result["result_msg"])
        # self.assertEqual(expected["result_message"], result["result_msg"])
        self.assertEqual(expected["origin"], result["origin"])
        self.assertEqual(expected["xml"], result["detail"]["xml"])
        mock_pid_provider_xml_save.assert_not_called()
        mock_pid_request_save.assert_called_once_with()


@patch(
    "pid_provider.models.utcnow",
    side_effect=[datetime(2020, 2, 2, 0, 0), datetime(2020, 2, 3, 0, 0)],
)
@patch("pid_provider.models.XMLSPS.save")
@patch("pid_provider.models.XMLVersion.save_file")
@patch("pid_provider.models.XMLVersion.save")
@patch("pid_provider.models.XMLIssue.save")
@patch("pid_provider.models.XMLJournal.save")
@patch("pid_provider.models.PidProviderXML.save")
@patch("pid_provider.models.PidRequest.save")
class PidProviderXMLRegisterTest(TestCase):
    def test_register_with_success(
        self,
        mock_pid_request_save,
        mock_pid_provider_xml_save,
        mock_xml_journal_save,
        mock_xml_issue_save,
        mock_xml_version_save,
        mock_xml_version_save_file,
        mock_xml_sps_save,
        mock_now,
    ):
        expected = {
            "result_type": "<class 'pid_provider.exceptions.NotEnoughParametersToGetDocumentRecordError'>",
            "result_message": "No attribute enough for disambiguations {'z_surnames': None, 'z_collab': None, 'main_doi': None, 'z_links': None, 'z_partial_body': None, 'pkg_name': None, 'elocation_id': None, 'journal__issn_print': None, 'journal__issn_electronic': None, 'article_pub_year': None}",
            "origin": "filename.xml",
            "xml": "<article/>",
        }

        user = User()
        xml_adapter = _get_xml_adapter_from_file(
            "./pid_provider/fixtures/article/ex-aop.xml"
        )
        result = models.PidProviderXML.register(
            xml_with_pre=xml_adapter.xml_with_pre,
            filename="ex-aop.xml",
            user=user,
        )
        self.assertEqual("yH6CLqxFJsQKrHj7zXkwL3G", result["v3"])
        self.assertEqual("S1413-41522020000400627", result["v2"])
        self.assertEqual("S1413-41522020005000111", result["aop_pid"])
        self.assertEqual("1809-4457-esa-25-04-627", result["pkg_name"])
        self.assertEqual(False, result["xml_changed"])
        self.assertEqual("created", result["record_status"])
        self.assertIsNone(result["updated"])
        self.assertIsNotNone(result["created"])
        mock_pid_request_save.assert_not_called()


class XMLURLTest(TestCase):
    """Tests for XMLURL model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.test_url = "http://example.com/article.xml"
        self.test_pid = "ABC123XYZ456"
        
    def test_create_xmlurl(self):
        """Test creating a new XMLURL instance"""
        xmlurl = models.XMLURL.create(
            user=self.user,
            url=self.test_url,
            status="pending",
            pid=self.test_pid,
        )
        
        self.assertIsNotNone(xmlurl)
        self.assertEqual(xmlurl.url, self.test_url)
        self.assertEqual(xmlurl.status, "pending")
        self.assertEqual(xmlurl.pid, self.test_pid)
        self.assertEqual(xmlurl.creator, self.user)
        
    def test_get_xmlurl(self):
        """Test getting an XMLURL by URL"""
        models.XMLURL.create(
            user=self.user,
            url=self.test_url,
            status="pending",
            pid=self.test_pid,
        )
        
        xmlurl = models.XMLURL.get(url=self.test_url)
        self.assertIsNotNone(xmlurl)
        self.assertEqual(xmlurl.url, self.test_url)
        
    def test_create_or_update_existing(self):
        """Test updating an existing XMLURL"""
        # Create initial record
        xmlurl = models.XMLURL.create(
            user=self.user,
            url=self.test_url,
            status="pending",
            pid=None,
        )
        
        # Update it
        updated_xmlurl = models.XMLURL.create_or_update(
            user=self.user,
            url=self.test_url,
            status="success",
            pid=self.test_pid,
        )
        
        self.assertEqual(updated_xmlurl.id, xmlurl.id)
        self.assertEqual(updated_xmlurl.status, "success")
        self.assertEqual(updated_xmlurl.pid, self.test_pid)
        self.assertEqual(updated_xmlurl.updated_by, self.user)
        
    def test_create_or_update_new(self):
        """Test creating a new XMLURL when it doesn't exist"""
        xmlurl = models.XMLURL.create_or_update(
            user=self.user,
            url=self.test_url,
            status="pending",
            pid=self.test_pid,
        )
        
        self.assertIsNotNone(xmlurl)
        self.assertEqual(xmlurl.url, self.test_url)
        self.assertEqual(xmlurl.status, "pending")
        
    def test_save_file_with_string_content(self):
        """Test save_file method with string XML content"""
        xmlurl = models.XMLURL.create(
            user=self.user,
            url=self.test_url,
            status="pending",
            pid=self.test_pid,
        )
        
        xml_content = "<article><title>Test Article</title></article>"
        result = xmlurl.save_file(xml_content, filename="test.xml")
        
        self.assertTrue(result)
        self.assertTrue(xmlurl.zipfile.name)
        
    def test_save_file_with_bytes_content(self):
        """Test save_file method with bytes XML content"""
        xmlurl = models.XMLURL.create(
            user=self.user,
            url=self.test_url,
            status="pending",
            pid=self.test_pid,
        )
        
        xml_content = b"<article><title>Test Article</title></article>"
        result = xmlurl.save_file(xml_content, filename="test.xml")
        
        self.assertTrue(result)
        self.assertTrue(xmlurl.zipfile.name)
        
    def test_save_file_default_filename(self):
        """Test save_file method with default filename"""
        xmlurl = models.XMLURL.create(
            user=self.user,
            url=self.test_url,
            status="pending",
            pid=self.test_pid,
        )
        
        xml_content = "<article><title>Test Article</title></article>"
        result = xmlurl.save_file(xml_content)
        
        self.assertTrue(result)
        self.assertTrue(xmlurl.zipfile.name)
        
    def test_str_method(self):
        """Test __str__ method"""
        xmlurl = models.XMLURL.create(
            user=self.user,
            url=self.test_url,
            status="pending",
            pid=self.test_pid,
        )
        
        expected_str = f"{self.test_url} - pending"
        self.assertEqual(str(xmlurl), expected_str)


class BasePidProviderXMLURITest(TestCase):
    """Tests for BasePidProvider.provide_pid_for_xml_uri method"""
    
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        
    @patch("pid_provider.base_pid_provider.XMLWithPre.create")
    def test_provide_pid_for_xml_uri_fetch_failure(self, mock_create):
        """Test exception type a) - Failure to obtain XML"""
        from pid_provider.base_pid_provider import BasePidProvider
        
        # Mock XMLWithPre.create to raise an exception
        mock_create.side_effect = Exception("Connection timeout")
        
        provider = BasePidProvider()
        result = provider.provide_pid_for_xml_uri(
            xml_uri="http://example.com/article.xml",
            name="test.xml",
            user=self.user,
        )
        
        # Should return error details
        self.assertIn("error_msg", result)
        self.assertIn("error_type", result)
        
        # Should create XMLURL with failed status
        xmlurl = models.XMLURL.get(url="http://example.com/article.xml")
        self.assertEqual(xmlurl.status, "xml_fetch_failed")
        self.assertIsNone(xmlurl.pid)
        
    @patch("pid_provider.base_pid_provider.XMLWithPre.create")
    @patch.object(models.PidProviderXML, "register")
    def test_provide_pid_for_xml_uri_success(self, mock_register, mock_create):
        """Test successful processing with XMLURL creation"""
        from pid_provider.base_pid_provider import BasePidProvider
        
        # Mock XMLWithPre.create
        xml_with_pre = _get_xml_with_pre("<article><title>Test</title></article>")
        mock_create.return_value = [xml_with_pre]
        
        # Mock successful registration
        mock_register.return_value = {
            "v3": "test_v3_pid",
            "v2": "test_v2_pid",
            "created": datetime.now(),
        }
        
        provider = BasePidProvider()
        result = provider.provide_pid_for_xml_uri(
            xml_uri="http://example.com/article.xml",
            name="test.xml",
            user=self.user,
        )
        
        # Should return success response
        self.assertEqual(result.get("v3"), "test_v3_pid")
        
        # Should create XMLURL with success status
        xmlurl = models.XMLURL.get(url="http://example.com/article.xml")
        self.assertEqual(xmlurl.status, "success")
        self.assertEqual(xmlurl.pid, "test_v3_pid")
        
    @patch("pid_provider.base_pid_provider.XMLWithPre.create")
    @patch.object(models.PidProviderXML, "register")
    def test_provide_pid_for_xml_uri_registration_failure(self, mock_register, mock_create):
        """Test exception type b) - XML obtained but registration failed"""
        from pid_provider.base_pid_provider import BasePidProvider
        
        # Mock XMLWithPre.create
        xml_with_pre = _get_xml_with_pre("<article><title>Test</title></article>")
        mock_create.return_value = [xml_with_pre]
        
        # Mock failed registration
        mock_register.return_value = {
            "error_type": "ValidationError",
            "error_message": "Invalid XML structure",
            "v3": "test_v3_pid",
        }
        
        provider = BasePidProvider()
        result = provider.provide_pid_for_xml_uri(
            xml_uri="http://example.com/article2.xml",
            name="test2.xml",
            user=self.user,
        )
        
        # Should return error response
        self.assertIn("error_type", result)
        
        # Should create XMLURL with failed status and save zipfile
        xmlurl = models.XMLURL.get(url="http://example.com/article2.xml")
        self.assertEqual(xmlurl.status, "pid_provider_xml_failed")
        self.assertEqual(xmlurl.pid, "test_v3_pid")
