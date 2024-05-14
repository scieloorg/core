import logging
import sys

from django.db.models import Q
from django.db.utils import DataError
from lxml import etree
from packtools.sps.models.article_abstract import ArticleAbstract
from packtools.sps.models.article_and_subarticles import ArticleAndSubArticles
from packtools.sps.models.article_authors import Authors
from packtools.sps.models.article_doi_with_lang import DoiWithLang
from packtools.sps.models.article_ids import ArticleIds
from packtools.sps.models.article_license import ArticleLicense
from packtools.sps.models.article_titles import ArticleTitles
from packtools.sps.models.article_toc_sections import ArticleTocSections
from packtools.sps.models.dates import ArticleDates
from packtools.sps.models.front_articlemeta_issue import ArticleMetaIssue
from packtools.sps.models.funding_group import FundingGroup
from packtools.sps.models.journal_meta import ISSN, Title
from packtools.sps.models import journal_meta
from packtools.sps.models.kwd_group import ArticleKeywords
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre

from article.models import Article, ArticleFunding, DocumentAbstract, DocumentTitle
from article.utils.parse_name_author import get_safe_value
from core.forms import CoreAdminModelForm
from core.models import Language, License, LicenseStatement
from doi.models import DOI
from institution.models import Sponsor, Publisher
from issue.models import Issue, TocSection
from journal.models import Journal, OfficialJournal
from researcher.exceptions import PersonNameCreateError
from researcher.models import Researcher, InstitutionalAuthor, Affiliation
from tracker.models import UnexpectedEvent
from vocabulary.models import Keyword
from location.models import Location


class XMLSPSArticleSaveError(Exception):
    ...


class LicenseDoesNotExist(Exception):
    ...


def load_article(user, xml=None, file_path=None, v3=None):
    logging.info(f"load article {file_path} {v3}")
    try:
        if file_path:
            for xml_with_pre in XMLWithPre.create(file_path):
                xmltree = xml_with_pre.xmltree
                break
        elif xml:
            xml_with_pre = XMLWithPre("", etree.fromstring(xml))
        else:
            raise ValueError(
                "article.sources.xmlsps.load_article requires xml or file_path"
            )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            item=file_path or v3,
            action="article.sources.xmlsps.load_article",
            exception=e,
            exc_traceback=exc_traceback,
            detail=dict(
                function="article.sources.xmlsps.load_article",
                xml=f"{xml}",
                v3=v3,
                file_path=file_path,
            ),
        )
        return

    pid_v3 = v3 or xml_with_pre.v3

    try:
        article = Article.objects.get(pid_v3=pid_v3)
    except Article.DoesNotExist:
        article = Article()
    try:
        xmltree = xml_with_pre.xmltree
        article.valid = False
        article.sps_pkg_name = xml_with_pre.sps_pkg_name
        set_pids(xmltree=xmltree, article=article)
        article.journal = get_journal(xmltree=xmltree)
        set_date_pub(xmltree=xmltree, article=article)
        article.article_type = get_or_create_article_type(xmltree=xmltree, user=user)
        article.issue = get_or_create_issues(xmltree=xmltree, user=user, item=pid_v3)
        set_first_last_page_elocation_id(xmltree=xmltree, article=article)
        article.save()

        article.titles.set(
            create_or_update_titles(xmltree=xmltree, user=user, item=pid_v3)
        )
        article.abstracts.set(
            create_or_update_abstract(
                xmltree=xmltree, user=user, article=article, item=pid_v3
            )
        )
        article.researchers.set(
            create_or_update_researchers(xmltree=xmltree, user=user, item=pid_v3)
        )
        article.collab.set(
            get_or_create_institution_authors(xmltree=xmltree, user=user, item=pid_v3)
        )
        article.keywords.set(
            create_or_update_keywords(xmltree=xmltree, user=user, item=pid_v3)
        )

        article.languages.add(get_or_create_main_language(xmltree=xmltree, user=user))
        article.toc_sections.set(get_or_create_toc_sections(xmltree=xmltree, user=user))
        article.fundings.set(
            get_or_create_fundings(xmltree=xmltree, user=user, item=pid_v3)
        )
        article.doi.set(get_or_create_doi(xmltree=xmltree, user=user))

        article.license_statements.set(get_licenses(xmltree=xmltree, user=user))
        for ls in article.license_statements.iterator():
            article.license = ls.license
            article.save()
            break
        article.publisher = get_or_create_publisher(xmltree=xmltree, user=user, item=pid_v3)
        article.valid = True
        article.save()
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        xml_detail_error = etree.tostring(xmltree)
        UnexpectedEvent.create(
            item=pid_v3,
            action="article.sources.xmlsps.load_article",
            exception=e,
            exc_traceback=exc_traceback,
            detail=dict(
                function="article.sources.xmlsps.load_article",
                message=f"{xml_detail_error}",
            ),
        )


def get_or_create_doi(xmltree, user):
    doi_with_lang = DoiWithLang(xmltree=xmltree).data
    data = []
    for doi in doi_with_lang:
        obj = DOI.get_or_create(
            value=doi.get("value"),
            language=get_or_create_language(doi.get("lang"), user=user),
            creator=user,
        )
        data.append(obj)
    return data


def get_journal(xmltree):
    try:
        return Journal.objects.get(title=Title(xmltree=xmltree).journal_title)
    except (Journal.DoesNotExist, Journal.MultipleObjectsReturned):
        pass

    issn = ISSN(xmltree=xmltree)
    journal_issn_epub = issn.epub
    journal_issn_ppub = issn.ppub
    try:
        official_journal = OfficialJournal.get(
            issn_print=journal_issn_ppub, issn_electronic=journal_issn_epub
        )
        return Journal.objects.get(official=official_journal)
    except (OfficialJournal.DoesNotExist, Journal.DoesNotExist):
        return None


def get_or_create_publisher(xmltree, user, item):
    try:
        publisher_names = journal_meta.Publisher(xmltree=xmltree).publishers_names
        if publisher_names:
            return Publisher.get_or_create(
                user=user,
                name=publisher_names[0],
                acronym=None,
                level_1=None,
                level_2=None,
                level_3=None,
                location=None,
                official=None,
                is_official=None,
                url=None,
                institution_type=None,
            )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            item=item,
            action="article.xmlsps.get_or_create_publisher",
            exception=e,
            exc_traceback=exc_traceback,
            detail=dict(
                function="article.xmlsps.get_or_create_publisher",
                publisher_name=publisher_names,
            ),
        )


def get_or_create_fundings(xmltree, user, item):
    """
    Ex fundings_group:
    [{'funding-source': ['CNPQ'], 'award-id': ['12345', '67890']},
        {'funding-source': ['FAPESP'], 'award-id': ['23456', '56789']},]
    """

    fundings_group = FundingGroup(xmltree=xmltree).award_groups
    data = []
    if fundings_group:
        for funding in fundings_group:
            funding_source = funding.get("funding-source") or []
            award_ids = funding.get("award-id") or []

            for fs in funding_source:
                sponsor = create_or_update_sponsor(
                    funding_name=fs, user=user, item=item
                )
                for award_id in award_ids:
                    try:
                        obj = ArticleFunding.get_or_create(
                            award_id=award_id,
                            funding_source=sponsor,
                            user=user,
                        )
                        if obj:
                            data.append(obj)
                    except Exception as e:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        UnexpectedEvent.create(
                            item=item,
                            action="article.xmlsps.sources.get_or_create_fundings",
                            exception=e,
                            exc_traceback=exc_traceback,
                            detail=dict(
                                xmltree=f"{etree.tostring(xmltree)}",
                                function="article.xmlsps.sources.get_or_create_fundings",
                                funding_source=fs,
                                award_id=award_id,
                            ),
                        )
    return data


def get_or_create_toc_sections(xmltree, user):
    toc_sections = ArticleTocSections(xmltree=xmltree).all_section_dict
    data = []
    for key, value in toc_sections.items():
        if key and value:
            obj = TocSection.get_or_create(
                value=value,
                language=get_or_create_language(key, user=user),
                user=user,
            )
            data.append(obj)
    return data


def get_licenses(xmltree, user):
    xml_licenses = ArticleLicense(xmltree=xmltree).licenses
    data = []
    license = None
    for xml_license in xml_licenses:

        if not license and xml_license.get("link"):
            url_data = LicenseStatement.parse_url(xml_license.get("link"))
            license_type = url_data.get("license_type")
            if license_type:
                license = License.create_or_update(
                    user=user,
                    license_type=license_type,
                )
        if license or xml_license.get("license_p"):
            try:
                license_p = xml_license.get("license_p")
                license_p = license_p["html_text"]
            except (ValueError, TypeError, KeyError):
                pass

            obj = LicenseStatement.create_or_update(
                user=user,
                url=xml_license.get("link"),
                language=Language.get_or_create(code2=xml_license.get("lang")),
                license_p=license_p,
                license=license,
            )
            data.append(obj)
    return data


def create_or_update_keywords(xmltree, user, item):
    article_keywords = ArticleKeywords(xmltree=xmltree)
    article_keywords.configure(tags_to_convert_to_html={'bold': 'b'})
    data = []
    for kwd in article_keywords.items:
        try:
            obj = Keyword.create_or_update(
                user=user,
                vocabulary=None,
                language=get_or_create_language(kwd.get("lang"), user=user),
                text=kwd.get("plain_text"),
                html_text=kwd.get("html_text"),
            )
            data.append(obj)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                item=item,
                action="article.xmlsps.get_or_create_keywords",
                exception=e,
                exc_traceback=exc_traceback,
                detail=dict(
                    xmltree=f"{etree.tostring(xmltree)}",
                    function="article.xmlsps.get_or_create_keywords",
                    keyword=kwd,
                ),
            )
    return data


def create_or_update_abstract(xmltree, user, article, item):
    data = []
    abstract = ArticleAbstract(xmltree=xmltree)
    abstract.configure(tags_to_convert_to_html={'bold': 'b', 'italic': 'i'})

    if xmltree.find(".//abstract") is not None:
        try:
            for ab in abstract.get_abstracts():
                if ab:
                    obj = DocumentAbstract.create_or_update(
                        user=user,
                        article=article,
                        language=get_or_create_language(ab.get("lang"), user=user),
                        text=ab.get("plain_text"),
                        rich_text=ab.get("html_text"),
                    )
                    data.append(obj)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                item=item,
                action="article.xmlsps.sources.create_or_update_abstract",
                exception=e,
                exc_traceback=exc_traceback,
                detail=dict(
                    xmltree=f"{etree.tostring(xmltree)}",
                    function="article.xmlsps.sources.create_or_update_abstract",
                ),
            )
    return data


def create_or_update_researchers(xmltree, user, item):
    try:
        article_lang = ArticleAndSubArticles(xmltree=xmltree).main_lang
    except Exception as e:
        article_lang = None

    authors = Authors(xmltree=xmltree).contribs_with_affs

    # Falta gender e gender_identification_status
    data = []
    for author in authors:
        try:
            researcher_data = {
                "user": user,
                "given_names": author.get("given_names"),
                "last_name": author.get("surname"),
                "suffix": author.get("suffix"),
                "lang": article_lang,
                "orcid": author.get("orcid"),
                "lattes": author.get("lattes"),
                "email": author.get("email"),
                "gender": author.get("gender"),
                "gender_identification_status": author.get(
                    "gender_identification_status"
                ),
            }

            affs = author.get("affs", [])
            if not affs:
                obj = Researcher.create_or_update(**researcher_data)
                data.append(obj)
            else:
                for aff in affs:
                    email = author.get("email") or aff.get("email")
                    aff_data = {
                        **researcher_data,
                        "aff_name": get_safe_value(aff, "orgname"),
                        "aff_div1": get_safe_value(aff, "orgdiv1"),
                        "aff_div2": get_safe_value(aff, "orgdiv2"),
                        "aff_city_name": get_safe_value(aff, "city"),
                        "aff_country_acronym": get_safe_value(aff, "country_code"),
                        "aff_country_name": get_safe_value(aff, "country_name"),
                        "aff_state_text": get_safe_value(aff, "state"),
                        "email": email,
                    }
                    obj = Researcher.create_or_update(**aff_data)
                    data.append(obj)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                item=item,
                action="article.xmlsps.create_or_update_researchers",
                exception=e,
                exc_traceback=exc_traceback,
                detail=dict(
                    xmltree=f"{etree.tostring(xmltree)}",
                    function="article.xmlsps.create_or_update_researchers",
                    author=author,
                    affiliation=affs,
                ),
            )
    return data


def get_or_create_institution_authors(xmltree, user, item):
    data = []
    authors = Authors(xmltree=xmltree).contribs_with_affs
    for author in authors:
        try:
            affiliation = None
            if collab := author.get("collab"):
                if affs := author.get("affs"):
                    for aff in affs:
                        location = Location.create_or_update(
                            user=user,
                            country_name=aff.get("country_name"),
                            state_name=aff.get("state"),
                            city_name=aff.get("city"),
                        )
                        affiliation = Affiliation.create_or_update(
                            name=aff.get("orgname"),
                            acronym=None,
                            level_1=aff.get("orgdiv1"),
                            level_2=aff.get("orgdiv2"),
                            level_3=None,
                            location=location,
                            official=None,
                            is_official=None,
                            url=None,
                            institution_type=None,
                            user=user,
                        )
                obj = InstitutionalAuthor.get_or_create(
                    collab=collab,
                    affiliation=affiliation,
                    user=user,
                )
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                item=item,
                action="article.xmlsps.get_or_create_institution_authors",
                exception=e,
                exc_traceback=exc_traceback,
                detail=dict(
                    xmltree=f"{etree.tostring(xmltree)}",
                    function="article.xmlsps.get_or_create_institution_authors",
                    author=author,
                ),
            )
    return data


def set_pids(xmltree, article):
    pids = ArticleIds(xmltree=xmltree).data
    if pids.get("v2") or pids.get("v3"):
        article.set_pids(pids)


def set_date_pub(xmltree, article):
    dates = ArticleDates(xmltree=xmltree).article_date
    article.set_date_pub(dates)


def set_first_last_page_elocation_id(xmltree, article):
    xml = ArticleMetaIssue(xmltree=xmltree)
    article.first_page = xml.fpage
    article.last_page = xml.lpage
    article.elocation_id = xml.elocation_id


def create_or_update_titles(xmltree, user, item):
    titles = ArticleTitles(xmltree=xmltree,  tags_to_convert_to_html={'bold': 'b'}).article_title_list
    data = []
    for title in titles:
        try:
            lang = get_or_create_language(title.get("lang"), user=user)
            obj = DocumentTitle.create_or_update(
                title=title.get("plain_text"),
                rich_text=title.get("html_text"),
                language=lang,
                user=user,
            )
            data.append(obj)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                item=item,
                action="article.sources.xmlsps.create_or_update_titles",
                exception=e,
                exc_traceback=exc_traceback,
                detail=dict(
                    xmltree=f"{etree.tostring(xmltree)}",
                    function="article.sources.xmlsps.create_or_update_titles",
                    title=title.get("plain_text"),
                    language=lang,
                ),
            )
    return data


def get_or_create_article_type(xmltree, user):
    article_type = ArticleAndSubArticles(xmltree=xmltree).main_article_type
    return article_type


def get_or_create_issues(xmltree, user, item):
    issue_data = ArticleMetaIssue(xmltree=xmltree).data
    collection_date = ArticleDates(xmltree=xmltree).collection_date
    try:
        obj = Issue.get_or_create(
            journal=get_journal(xmltree=xmltree),
            number=issue_data.get("number"),
            volume=issue_data.get("volume"),
            season=collection_date.get("season"),
            year=collection_date.get("year"),
            month=collection_date.get("month"),
            supplement=collection_date.get("suppl"),
            user=user,
        )
        return obj
    except AttributeError as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            item=item,
            action="article.xmlsps.get_or_create_issues",
            exception=e,
            exc_traceback=exc_traceback,
            detail=dict(
                xmltree=f"{etree.tostring(xmltree)}",
                function="article.xmlsps.get_or_create_issues",
                issue=issue_data,
            ),
        )


def get_or_create_language(lang, user):
    obj = Language.get_or_create(code2=lang, creator=user)
    return obj


def get_or_create_main_language(xmltree, user):
    lang = ArticleAndSubArticles(xmltree=xmltree).main_lang
    obj = get_or_create_language(lang, user)
    return obj


def create_or_update_sponsor(funding_name, user, item):
    try:
        return Sponsor.get_or_create(
            user=user,
            name=funding_name,
            acronym=None,
            level_1=None,
            level_2=None,
            level_3=None,
            location=None,
            official=None,
            is_official=None,
            url=None,
            institution_type=None,
        )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            item=item,
            action="article.xmlsps.create_or_update_sponsor",
            exception=e,
            exc_traceback=exc_traceback,
            detail=dict(
                function="article.xmlsps.create_or_update_sponsor",
                funding_name=funding_name,
            ),
        )
