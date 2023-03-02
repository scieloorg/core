import hashlib
import logging
import os
from copy import deepcopy
from datetime import datetime, date
from zipfile import ZipFile, BadZipFile
from shutil import copyfile

from django.utils.translation import gettext as _
import requests
from lxml import etree
from packtools.sps.models.article_ids import ArticleIds
from packtools.sps.models.article_doi_with_lang import DoiWithLang
from packtools.sps.models.front_journal_meta import ISSN
from packtools.sps.models.front_articlemeta_issue import ArticleMetaIssue
from packtools.sps.models.article_authors import Authors
from packtools.sps.models.article_titles import ArticleTitles
from packtools.sps.models.body import Body
from packtools.sps.models.dates import ArticleDates
from packtools.sps.models.related_articles import RelatedItems
from packtools.sps.models.article_assets import (
    ArticleAssets,
    SupplementaryMaterials,
)
from packtools.sps.models.article_renditions import (
    ArticleRenditions,
)

from files_storage.utils import generate_finger_print


LOGGER = logging.getLogger(__name__)
LOGGER_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class GetXmlWithPreError(Exception):
    ...


class GetXmlWithPreFromURIError(Exception):
    ...


class GetXMLItemsError(Exception):
    ...


class GetXMLItemsFromZipFileError(Exception):
    ...


def get_xml_items(xml_sps_file_path, filenames=None):
    """
    Get XML items from XML file or Zip file

    Arguments
    ---------
        xml_sps_file_path: str

    Return
    ------
    dict iterator which keys are filename and xml_with_pre

    Raises
    ------
    GetXMLItemsError
    """
    try:
        name, ext = os.path.splitext(xml_sps_file_path)
        if ext == ".zip":
            return get_xml_items_from_zip_file(xml_sps_file_path, filenames)
        if ext == ".xml":
            with open(xml_sps_file_path) as fp:
                xml = get_xml_with_pre(fp.read())
                item = os.path.basename(xml_sps_file_path)
            return [{"filename": item, "xml_with_pre": xml}]
        raise ValueError(
            _("{} must be xml file or zip file containing xml").format(
                xml_sps_file_path
            )
        )
    except Exception as e:
        LOGGER.exception(e)
        raise GetXMLItemsError(
            _("Unable to get xml items from {}: {} {}").format(
                xml_sps_file_path, type(e), e
            )
        )


def get_xml_items_from_zip_file(xml_sps_file_path, filenames=None):
    """
    Return the first XML content in the Zip file.

    Arguments
    ---------
        xml_sps_file_path: str
        filenames: str list

    Return
    ------
    str
    """
    try:
        with ZipFile(xml_sps_file_path) as zf:
            filenames = filenames or zf.namelist() or []
            for item in filenames:
                if item.endswith(".xml"):
                    yield {
                        "filename": item,
                        "xml_with_pre": get_xml_with_pre(zf.read(item).decode("utf-8")),
                    }
    except Exception as e:
        LOGGER.exception(e)
        raise GetXMLItemsFromZipFileError(
            _("Unable to get xml items from zip file {}: {} {}").format(
                xml_sps_file_path, type(e), e
            )
        )


def update_zip_file_xml(xml_sps_file_path, xml_file_path, content):
    """
    Save XML content in a Zip file.
    Return saved zip file path

    Arguments
    ---------
        xml_sps_file_path: str
        content: bytes

    Return
    ------
    str
    """
    with ZipFile(xml_sps_file_path, "w") as zf:
        LOGGER.debug(
            "Try to write xml %s %s %s"
            % (xml_sps_file_path, xml_file_path, content[:100])
        )
        zf.writestr(xml_file_path, content)

    return os.path.isfile(xml_sps_file_path)


def create_xml_zip_file(xml_sps_file_path, content):
    """
    Save XML content in a Zip file.
    Return saved zip file path

    Arguments
    ---------
        xml_sps_file_path: str
        content: bytes

    Return
    ------
    bool

    Raises
    ------
    IOError
    """
    dirname = os.path.dirname(xml_sps_file_path)
    if dirname and not os.path.isdir(dirname):
        os.makedirs(dirname)

    basename = os.path.basename(xml_sps_file_path)
    name, ext = os.path.splitext(basename)

    with ZipFile(xml_sps_file_path, "w") as zf:
        zf.writestr(name + ".xml", content)
    return os.path.isfile(xml_sps_file_path)


def get_xml_with_pre_from_uri(uri, timeout=30):
    try:
        response = requests.get(uri, timeout=timeout)
        xml_content = response.content.decode("utf-8")
    except Exception as e:
        raise GetXmlWithPreFromURIError(_("Unable to get xml from {}").format(uri))
    return get_xml_with_pre(xml_content)


def get_xml_with_pre(xml_content):
    try:
        # return etree.fromstring(xml_content)
        pref, xml = split_processing_instruction_doctype_declaration_and_xml(
            xml_content
        )
        return XMLWithPre(pref, etree.fromstring(xml))

    except Exception as e:
        raise GetXmlWithPreError(
            "Unable to get xml with pre %s ... %s"
            % (xml_content[:100], xml_content[-200:])
        )


def split_processing_instruction_doctype_declaration_and_xml(xml_content):
    xml_content = xml_content.strip()

    if not xml_content.startswith("<?") and not xml_content.startswith("<!"):
        return "", xml_content

    if xml_content.endswith("/>"):
        # <article/>
        p = xml_content.rfind("<")
        if p >= 0:
            pre = xml_content[:p].strip()
            if pre.endswith(">"):
                return xml_content[:p], xml_content[p:]
            else:
                return "", xml_content

    p = xml_content.rfind("</")
    if p:
        # </article>
        endtag = xml_content[p:]
        starttag1 = endtag.replace("/", "").replace(">", " ")
        starttag2 = endtag.replace("/", "")
        for starttag in (starttag1, starttag2):
            p = xml_content.find(starttag)
            if p >= 0:
                pre = xml_content[:p].strip()
                if pre.endswith(">"):
                    return xml_content[:p], xml_content[p:]
                else:
                    return "", xml_content

    return "", xml_content


class XMLWithPre:
    """
    Preserva o texto anterior ao elemento `root`
    """

    def __init__(self, xmlpre, xmltree):
        self.xmlpre = xmlpre or ""
        self.xmltree = xmltree

    def tostring(self):
        return self.xmlpre + etree.tostring(self.xmltree, encoding="utf-8").decode(
            "utf-8"
        )

    @property
    def finger_print(self):
        return generate_finger_print(etree.tostring(self.xmltree, encoding="utf-8"))

    def update_ids(self, v3, v2, aop_pid):
        # update IDs
        self.article_ids.v3 = v3
        self.article_ids.v2 = v2
        if aop_pid:
            self.article_ids.aop_pid = aop_pid

    @property
    def related_items(self):
        if not hasattr(self, "_related_items") or not self._related_items:
            # list of dict which keys are
            # href, ext-link-type, related-article-type
            items = RelatedItems(self.xmltree)
            self._related_items = list(items.related_articles)
        return self._related_items

    @property
    def article_ids(self):
        if not hasattr(self, "_article_ids") or not self._article_ids:
            # [{"lang": "en", "value": "DOI"}]
            self._article_ids = ArticleIds(self.xmltree)
        return self._article_ids

    @property
    def v3(self):
        return self.article_ids.v3

    @property
    def v2(self):
        return self.article_ids.v2

    @property
    def aop_pid(self):
        return self.article_ids.aop_pid

    @v3.setter
    def v3(self, value):
        self.article_ids.v3 = value

    @v2.setter
    def v2(self, value):
        self.article_ids.v2 = value

    @aop_pid.setter
    def aop_pid(self, value):
        self.article_ids.aop_pid = value

    @property
    def article_doi_with_lang(self):
        if (
            not hasattr(self, "_article_doi_with_lang")
            or not self._article_doi_with_lang
        ):
            # [{"lang": "en", "value": "DOI"}]
            doi_with_lang = DoiWithLang(self.xmltree)
            self._main_doi = doi_with_lang.main_doi
            self._article_doi_with_lang = doi_with_lang.data
        return self._article_doi_with_lang

    @property
    def main_doi(self):
        if not hasattr(self, "_main_doi") or not self._main_doi:
            # [{"lang": "en", "value": "DOI"}]
            doi_with_lang = DoiWithLang(self.xmltree)
            self._main_doi = doi_with_lang.main_doi
        return self._main_doi

    @property
    def main_toc_section(self):
        """
        <subj-group subj-group-type="heading">
            <subject>Articles</subject>
        </subj-group>
        """
        if not hasattr(self, "_main_toc_section") or not self._main_toc_section:
            # [{"lang": "en", "value": "DOI"}]
            node = self.xmltree.find('.//subj-group[@subj-group-type="heading"]')
            if node is None:
                self._main_toc_section = None
            else:
                self._main_toc_section = node.findtext("./subject")
        return self._main_toc_section

    @property
    def issns(self):
        if not hasattr(self, "_issns") or not self._issns:
            # [{"type": "epub", "value": "1234-9876"}]
            issns = ISSN(self.xmltree)
            self._issns = issns.data
        return self._issns

    @property
    def is_aop(self):
        if not hasattr(self, "_is_aop") or not self._is_aop:
            items = (
                self.article_in_issue["volume"],
                self.article_in_issue["number"],
                self.article_in_issue["suppl"],
            )
            self._is_aop = not any(items)
        return self._is_aop

    @property
    def article_in_issue(self):
        if not hasattr(self, "_article_in_issue") or not self._article_in_issue:
            _data = {
                "volume": None,
                "number": None,
                "suppl": None,
                "fpage": None,
                "fpage_seq": None,
                "lpage": None,
                "pub_year": None,
            }
            article_in_issue = ArticleMetaIssue(self.xmltree)
            _data.update(article_in_issue.data)
            if not _data.get("pub_year"):
                _data["pub_year"] = ArticleDates(self.xmltree).article_date["year"]

            if _data.get("pub_year"):
                _data["pub_year"] = int(_data["pub_year"])

            self._article_in_issue = _data
        return self._article_in_issue

    @property
    def authors(self):
        if not hasattr(self, "_authors") or not self._authors:
            authors = Authors(self.xmltree)
            self._authors = {
                "person": authors.contribs,
                "collab": authors.collab or None,
            }
        return self._authors

    @property
    def article_titles(self):
        if not hasattr(self, "_article_titles") or not self._article_titles:
            # list of dict which keys are lang and text
            article_titles = ArticleTitles(self.xmltree)
            self._article_titles = article_titles.data
        return self._article_titles

    @property
    def partial_body(self):
        if not hasattr(self, "_partial_body") or not self._partial_body:
            try:
                body = Body(self.xmltree)
                for text in body.main_body_texts:
                    if text:
                        self._partial_body = text
                        break
            except AttributeError:
                self._partial_body = None
        return self._partial_body

    @property
    def collab(self):
        if not hasattr(self, "_collab") or not self._collab:
            self._collab = self.authors.get("collab")
        return self._collab

    @property
    def journal(self):
        if not hasattr(self, "_journal") or not self._journal:
            # [{"type": "epub", "value": "1234-9876"}]
            journal = ISSN(self.xmltree)
            self._journal = {item["type"]: item["value"] for item in self.issns}
        return self._journal

    @property
    def article_publication_date(self):
        if (
            not hasattr(self, "_article_publication_date")
            or not self._article_publication_date
        ):
            # ("year", "month", "season", "day")
            _date = ArticleDates(self.xmltree).article_date
            self._article_publication_date = date(
                int(_date["year"]),
                int(_date["month"]),
                int(_date["day"]),
            )
        return self._article_publication_date

    @property
    def related_articles(self):
        if not hasattr(self, "_related_articles") or not self._related_articles:
            self._related_articles = self.xml_with_pre.related_items
        return self._related_articles

    @property
    def supplementary_materials(self):
        if (
            not hasattr(self, "_supplementary_materials")
            or not self._supplementary_materials
        ):
            supplmats = SupplementaryMaterials(self.xml_with_pre.xmltree)
            self._supplementary_materials = []
            names = [item.name for item in suppl_mats.items]
            for asset_file in self.assets_files:
                if asset_file.name in names:
                    asset_file.is_supplementary_material = True
                    asset_file.save()
                if asset_file.is_supplementary_material:
                    self._supplementary_materials.append(
                        {
                            "uri": asset_file.uri,
                            "lang": self.lang,
                            "ref_id": None,
                            "filename": asset_file.name,
                        }
                    )
        return self._supplementary_materials

    def get_assets(self, issue_assets_dict):
        """
        Atribui asset_files
        """
        if not hasattr(self, "_assets") or not self._assets:
            self._assets = []
            # obtém os assets do XML
            article_assets = ArticleAssets(self.xml_with_pre.xmltree)
            for asset_in_xml in article_assets.article_assets:
                asset = issue_assets_dict.get(asset_in_xml.name)
                if asset:
                    # FIXME tratar asset_file nao encontrado
                    self._assets.append(asset)
        return self._assets

    def get_xml_with_pre_with_remote_assets(
        self, v3=None, v2=None, aop_pid=None, assets_uris=None
    ):
        # FIXME assets de artigo pode estar em qq outra pasta do periódico
        # há casos em que os assets do artigo VoR está na pasta ahead
        if not hasattr(self, "_remote_xml") or not self._remote_xml:
            xml_with_pre = deepcopy(self)
            if v2 and not xml_with_pre.v2:
                xml_with_pre.v2 = v2
            if v3:
                xml_with_pre.v3 = v3
            if aop_pid:
                xml_with_pre.aop_pid = aop_pid
            if assets_uris:
                logging.info(f"REMOTE {assets_uris}")
                article_assets = ArticleAssets(xml_with_pre.xmltree)
                for item in article_assets.article_assets:
                    logging.info(item.name)
                not_found = article_assets.replace_names(assets_uris)
                for item in article_assets.article_assets:
                    logging.info(item.name)
                logging.info(not_found)
            self._remote_xml = xml_with_pre
        return self._remote_xml

    @property
    def langs(self):
        if not hasattr(self, "_langs") or not self._langs:
            article = ArticleRenditions(self.xml_with_pre.xmltree)
            renditions = article.article_renditions
            self._langs = []
            for rendition in renditions:
                self._langs.append(rendition.language)
        return self._langs
