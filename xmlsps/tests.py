from unittest.mock import patch, MagicMock
import os
from tempfile import TemporaryDirectory

from django.test import TestCase
from requests import HTTPError
from lxml import etree

from xmlsps import xml_sps_lib


# Create your tests here.
class GetXmlItemsTest(TestCase):

    @patch('xmlsps.xml_sps_lib.get_xml_items_from_zip_file')
    def test_zip(self, mock_get_xml_items_from_zip_file):
        result = xml_sps_lib.get_xml_items("file.zip")
        mock_get_xml_items_from_zip_file.assert_called_with(
            "file.zip", None
        )

    @patch('xmlsps.xml_sps_lib.get_xml_with_pre')
    @patch('xmlsps.xml_sps_lib.open')
    def test_xml(self, mock_open, mock_get_xml_with_pre):
        mock_get_xml_with_pre.return_value = "retorno"
        result = xml_sps_lib.get_xml_items("file.xml")
        mock_open.assert_called_with(
            "file.xml"
        )
        self.assertListEqual(
            [{"filename": "file.xml", "xml_with_pre": "retorno"}], result
        )

    def test_not_xml_and_not_zip(self):
        with self.assertRaises(xml_sps_lib.GetXMLItemsError) as exc:
            result = xml_sps_lib.get_xml_items("file.txt")
        self.assertIn("file.txt", str(exc.exception))


class GetXmlItemsFromZipFile(TestCase):
    def test_bad_zip_file(self):
        # xmlsps.xml_sps_lib.GetXMLItemsFromZipFileError
        with self.assertRaises(xml_sps_lib.GetXMLItemsFromZipFileError) as exc:
            items = list(xml_sps_lib.get_xml_items_from_zip_file("not_found.zip"))
        self.assertIn("not_found.zip", str(exc.exception))

    def test_good_zip_file(self):
        items = xml_sps_lib.get_xml_items_from_zip_file("xmlsps/fixtures/artigo.xml.zip")
        for item in items:
            self.assertEqual("artigo.xml", item['filename'])
            self.assertEqual(xml_sps_lib.XMLWithPre, type(item['xml_with_pre']))


class CreateXmlZipFileTest(TestCase):
    def test_create_file(self):
        with TemporaryDirectory() as dirname:
            file_path = os.path.join(dirname, "file.zip")
            result = xml_sps_lib.create_xml_zip_file(file_path, "<article/>")
            self.assertEqual(True, result)

    @patch('xmlsps.xml_sps_lib.ZipFile')
    def test_does_not_create_file(self, mock_ZipFile):
        with TemporaryDirectory() as dirname:
            mock_ZipFile.side_effect = OSError()
            file_path = os.path.join(dirname, "file.zip")
            with self.assertRaises(OSError):
                result = xml_sps_lib.create_xml_zip_file(file_path, "<article/>")


class GetXmlWithPreFromUriTest(TestCase):
    @patch("xmlsps.xml_sps_lib.requests.get")
    def test_get_xml_with_pre_from_uri(self, mock_get):
        class Resp:
            def __init__(self):
                self.content = b"<article/>"
        mock_get.return_value = Resp()
        result = xml_sps_lib.get_xml_with_pre_from_uri("URI")
        self.assertEqual(xml_sps_lib.XMLWithPre, type(result))

    @patch("xmlsps.xml_sps_lib.requests.get")
    def test_does_not_create_file(self, mock_get):
        mock_get.side_effect = HTTPError()
        with self.assertRaises(xml_sps_lib.GetXmlWithPreFromURIError) as exc:
            result = xml_sps_lib.get_xml_with_pre_from_uri("URI")
        self.assertIn("URI", str(exc.exception))


class GetXmlWithPreTest(TestCase):
    def test_get_xml_with_pre(self):
        result = xml_sps_lib.get_xml_with_pre("<article/>")
        self.assertEqual(xml_sps_lib.XMLWithPre, type(result))

    def test_does_not_return_xml_with_pre(self):
        with self.assertRaises(xml_sps_lib.GetXmlWithPreError):
            result = xml_sps_lib.get_xml_with_pre("<article")

    def test_empty_root_elem_and_incomplete_pre(self):
        with self.assertRaises(xml_sps_lib.GetXmlWithPreError) as exc:
            result = xml_sps_lib.get_xml_with_pre("<?proc<article/>")
        print(exc.exception)


class SplitProcessingInstructionDoctypeDeclarationAndXmlTest(TestCase):
    def test_processing_instruction_is_absent(self):
        result = xml_sps_lib.split_processing_instruction_doctype_declaration_and_xml("any")
        self.assertEqual("", result[0])
        self.assertEqual("any", result[1])

    def test_empty_root_elem(self):
        result = xml_sps_lib.split_processing_instruction_doctype_declaration_and_xml("<?proc?><article/>")
        self.assertEqual("<?proc?>", result[0])
        self.assertEqual("<article/>", result[1])

    def test_incomplete_root(self):
        result = xml_sps_lib.split_processing_instruction_doctype_declaration_and_xml("<?proc?><article")
        self.assertEqual("", result[0])
        self.assertEqual("<?proc?><article", result[1])

    def test_root_is_complete(self):
        result = xml_sps_lib.split_processing_instruction_doctype_declaration_and_xml("<?proc?><article></article>")
        self.assertEqual("<?proc?>", result[0])
        self.assertEqual("<article></article>", result[1])

    def test_mismatched_root(self):
        result = xml_sps_lib.split_processing_instruction_doctype_declaration_and_xml("<?proc?><article2></article>")
        self.assertEqual("", result[0])
        self.assertEqual("<?proc?><article2></article>", result[1])

    def test_empty_root_elem_and_incomplete_pre(self):
        result = xml_sps_lib.split_processing_instruction_doctype_declaration_and_xml("<?proc<article/>")
        self.assertEqual("", result[0])
        self.assertEqual("<?proc<article/>", result[1])

    def test_incomplete_root_and_incomplete_pre(self):
        result = xml_sps_lib.split_processing_instruction_doctype_declaration_and_xml("<?proc<article")
        self.assertEqual("", result[0])
        self.assertEqual("<?proc<article", result[1])

    def test_root_is_complete_and_incomplete_pre(self):
        result = xml_sps_lib.split_processing_instruction_doctype_declaration_and_xml("<?proc<article></article>")
        self.assertEqual("", result[0])
        self.assertEqual("<?proc<article></article>", result[1])


class XMLWithPreTest(TestCase):
    def _get_xml_with_pre(self, v2=None, v3=None, aop_pid=None):
        xml_v2 = (
            v2 and f'<article-id specific-use="scielo-v2">{v2}</article-id>' or
            ''
        )
        xml_v3 = (
            v3 and f'<article-id specific-use="scielo-v3">{v3}</article-id>' or
            ''
        )
        xml_aop_pid = (
            aop_pid and f'<article-id pub-id-type="publisher-id" specific-use="previous-pid">{aop_pid}</article-id>'
            or '')
        xml = f"""
        <article>
        <front>
        <article-meta>
        {xml_v2}
        {xml_v3}
        {xml_aop_pid}
        </article-meta>
        </front>
        </article>
        """
        return xml_sps_lib.XMLWithPre("", etree.fromstring(xml))

    def test_update_ids_v2_is_absent(self):
        xml_with_pre = self._get_xml_with_pre(v2=None)
        xml_with_pre.update_ids(v3='novo-v3', v2='novo', aop_pid=None)
        self.assertEqual('novo', xml_with_pre.v2)

    def test_update_ids_v3_is_absent(self):
        xml_with_pre = self._get_xml_with_pre(v3=None)
        xml_with_pre.update_ids(v3='novo', v2='novo-v2', aop_pid=None)
        self.assertEqual('novo', xml_with_pre.v3)

    def test_update_ids_aop_pid_is_absent(self):
        xml_with_pre = self._get_xml_with_pre(aop_pid=None)
        xml_with_pre.update_ids(v3='v3', v2='v2', aop_pid='novo')
        self.assertEqual('novo', xml_with_pre.aop_pid)

    def test_update_ids_v2_is_present_updating_is_forbidden(self):
        xml_with_pre = self._get_xml_with_pre(v2='current')
        with self.assertRaises(AttributeError) as exc:
            xml_with_pre.update_ids(v3='v3', v2='novo', aop_pid=None)
        self.assertIn('It is already set: current', str(exc.exception))

    def test_update_ids_v3_is_present_updating_is_allowed(self):
        xml_with_pre = self._get_xml_with_pre(v3='current')
        xml_with_pre.update_ids(v3='novo', v2='v2', aop_pid=None)
        self.assertEqual('novo', xml_with_pre.v3)

    def test_update_ids_aop_pid_is_present_updating_is_allowed(self):
        xml_with_pre = self._get_xml_with_pre(aop_pid='current')
        xml_with_pre.update_ids(v3='v3', v2='v2', aop_pid='novo')
        self.assertEqual('novo', xml_with_pre.aop_pid)
