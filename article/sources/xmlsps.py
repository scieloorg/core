import logging
import sys
from itertools import product

from lxml import etree
from packtools.sps.models.article_abstract import ArticleAbstract
from packtools.sps.models.article_and_subarticles import ArticleAndSubArticles
from packtools.sps.models.article_contribs import ArticleContribs, XMLContribs
from packtools.sps.models.article_doi_with_lang import DoiWithLang
from packtools.sps.models.article_ids import ArticleIds
from packtools.sps.models.article_license import ArticleLicense
from packtools.sps.models.article_titles import ArticleTitles
from packtools.sps.models.dates import ArticleDates
from packtools.sps.models.front_articlemeta_issue import ArticleMetaIssue
from packtools.sps.models.funding_group import FundingGroup
from packtools.sps.models.journal_meta import ISSN, Title
from packtools.sps.models.kwd_group import ArticleKeywords
from packtools.sps.models.v2.article_toc_sections import ArticleTocSections
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre

from article import choices
from article.exceptions import (
    LoadArticleAbstractError,
    LoadArticleCollabError,
    LoadArticleContribError,
    LoadArticleFundingError,
    LoadArticleIssueError,
    LoadArticleKeywordError,
    LoadArticleSponsorError,
    LoadArticleTitleError,
    LoadArticleTocSectionError,
)
from article.models import Article, ArticleFunding, DocumentAbstract, DocumentTitle
from core.models import Language
from core.utils.extracts_normalized_email import extracts_normalized_email
from doi.models import DOI
from institution.models import Sponsor
from issue.models import Issue, TocSection
from journal.models import Journal
from location.models import Location
from pid_provider.choices import PPXML_STATUS_DONE
from researcher.models import Affiliation, InstitutionalAuthor, Researcher
from tracker.models import UnexpectedEvent
from vocabulary.models import Keyword


def load_article(user, xml=None, file_path=None, v3=None, pp_xml=None):
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
        # Sequência organizada para atribuição de campos do Article
        # Do mais simples (campos diretos) para o mais complexo (FKs e M2M)
        errors = []
        xmltree = xml_with_pre.xmltree
        article = None

        # CRIAÇÃO/OBTENÇÃO DO OBJETO PRINCIPAL
        article = Article.get_or_create(pid_v3=pid_v3, user=user)
        article.valid = False
        article.data_status = choices.DATA_STATUS_PENDING
        article.pp_xml = pp_xml

        # CAMPOS SIMPLES EXTRAÍDOS DO XML (ainda tipos primitivos)
        article.sps_pkg_name = xml_with_pre.sps_pkg_name
        set_pids(
            xmltree=xmltree, article=article
        )  # Provavelmente define campos como pid, etc.
        set_date_pub(xmltree=xmltree, article=article)  # Define datas
        set_license(xmltree=xmltree, article=article)  # Define campos de licença
        set_first_last_page_elocation_id(
            xmltree=xmltree, article=article
        )  # Define paginação
        article.article_type = get_or_create_article_type(xmltree=xmltree, user=user)
        article.save()

        # FOREIGN KEYS SIMPLES (dependências diretas, sem muita complexidade)
        article.journal = get_journal(xmltree=xmltree)
        article.issue = get_or_create_issues(xmltree=xmltree, user=user, item=pid_v3)

        # MANY-TO-MANY
        article.languages.add(get_or_create_main_language(xmltree=xmltree, user=user))
        article.toc_sections.set(
            get_or_create_toc_sections(xmltree=xmltree, user=user, errors=errors)
        )
        article.titles.set(
            create_or_update_titles(xmltree=xmltree, user=user, item=pid_v3)
        )
        article.abstracts.set(
            create_or_update_abstract(
                xmltree=xmltree, user=user, article=article, item=pid_v3
            )
        )
        article.keywords.set(
            create_or_update_keywords(xmltree=xmltree, user=user, item=pid_v3)
        )
        article.researchers.set(
            create_or_update_researchers(xmltree=xmltree, user=user, item=pid_v3)
        )
        article.collab.set(
            get_or_create_institution_authors(xmltree=xmltree, user=user, item=pid_v3)
        )
        article.fundings.set(
            get_or_create_fundings(xmltree=xmltree, user=user, item=pid_v3)
        )
        article.doi.set(get_or_create_doi(xmltree=xmltree, user=user))

        # FINALIZAÇÃO
        article.valid = not (errors)  # Marca como válido após todas as atribuições
        # FIXME | TODO melhorar como identificar o valor adequado
        if article.valid:
            article.data_status = choices.DATA_STATUS_PUBLIC
        article.save()  # Persistência final

        if article.valid and article.pp_xml.proc_status != PPXML_STATUS_DONE:
            article.pp_xml.proc_status = PPXML_STATUS_DONE
            article.pp_xml.save()

        logging.info(f"The article {pid_v3} has been processed")
        return article
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        xml_detail_error = etree.tostring(xmltree)
        UnexpectedEvent.create(
            item=pid_v3,
            action="article.sources.xmlsps.load_article",
            exception=e,
            exc_traceback=exc_traceback,
            detail=dict(data=xml_detail_error),
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

    try:
        return Journal.get(
            issn_electronic=issn.epub,
            issn_print=issn.ppub,
        )
    except Journal.DoesNotExist:
        return None


def get_or_create_fundings(xmltree, user, item):
    """
    Ex fundings_award_group:
        [{
        'funding-source': ['São Paulo Research Foundation', 'CAPES', 'CNPq'],
        'award-id': ['2009/53363-8, 2009/52807-0, 2009/51766-8]}]
    """
    data = []
    fundings_award_group = FundingGroup(xmltree=xmltree).award_groups
    if fundings_award_group:
        for fundings_award in fundings_award_group:
            results = product(
                fundings_award.get("funding-source", []),
                fundings_award.get("award-id", []),
            )
            for result in results:
                try:
                    fs, award_id = result
                    if not fs or not award_id:
                        continue
                    if not fs:
                        raise LoadArticleFundingError(
                            f"get_or_create_fundings requires fs. Found {result}"
                        )
                    if not award_id:
                        raise LoadArticleFundingError(
                            f"get_or_create_fundings requires award_id. Found {result}"
                        )
                    sponsor = create_or_update_sponsor(
                        funding_name=fs, user=user, item=item
                    )
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
                            data=result,
                        ),
                    )
                    raise LoadArticleFundingError(e)
    return data


def get_or_create_toc_sections(xmltree, user, errors):
    toc_sections = ArticleTocSections(xmltree=xmltree).sections

    for item in toc_sections:
        section_title = item.get("section")
        section_lang = item.get("parent_lang")

        if not section_title and not section_lang:
            continue

        try:
            yield TocSection.get_or_create(
                value=section_title,
                language=get_or_create_language(section_lang, user=user),
                user=user,
            )
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            errors.append(
                {
                    "function": "get_or_create_toc_sections",
                    "item": item,
                    "error_type": str(type(e)),
                    "error_message": str(e),
                }
            )


def set_license(xmltree, article):
    xml_licenses = ArticleLicense(xmltree=xmltree).licenses
    for xml_license in xml_licenses:
        if license := xml_license.get("link"):
            article.article_license = license


def create_or_update_keywords(xmltree, user, item):
    article_keywords = ArticleKeywords(xmltree=xmltree)
    article_keywords.configure(tags_to_convert_to_html={"bold": "b"})
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
                    data=kwd,
                ),
            )
            raise LoadArticleKeywordError(e)
    return data


def create_or_update_abstract(xmltree, user, article, item):
    data = []
    abstract = ArticleAbstract(xmltree=xmltree)
    abstract.configure(tags_to_convert_to_html={"bold": "b", "italic": "i"})

    if xmltree.find(".//abstract") is not None:
        for ab in abstract.get_abstracts():
            if not ab:
                continue
            try:
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
                    detail=dict(data=ab),
                )
                raise LoadArticleAbstractError(e)
    return data


def create_or_update_researchers(xmltree, user, item):
    try:
        article_lang = ArticleAndSubArticles(xmltree=xmltree).main_lang
    except Exception as e:
        article_lang = None

    authors = XMLContribs(xmltree=xmltree).contribs

    # Falta gender e gender_identification_status
    data = []
    affs = None
    for author in authors:
        try:
            affs = None
            contrib_name = author.get("contrib_name", None)
            if contrib_name is not None:
                given_names = contrib_name.get("given-names")
                surname = contrib_name.get("surname")
                suffix = contrib_name.get("suffix")
            else:
                surname = None
                suffix = None
                given_names = None

            contrib_ids = author.get("contrib_ids", None)
            if contrib_ids is not None:
                orcid = contrib_ids.get("orcid")
                lattes = contrib_ids.get("lattes")
            else:
                orcid = None
                lattes = None

            researcher_data = {
                "user": user,
                "given_names": given_names,
                "last_name": surname,
                "suffix": suffix,
                "lang": article_lang,
                "orcid": orcid,
                "lattes": lattes,
                # "email": author.get("email"),
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
                    raw_email = author.get("email") or aff.get("email")
                    email = extracts_normalized_email(raw_email=raw_email)
                    aff_data = {
                        **researcher_data,
                        "aff_name": aff.get("orgname"),
                        "aff_div1": aff.get("orgdiv1"),
                        "aff_div2": aff.get("orgdiv2"),
                        "aff_city_name": aff.get("city"),
                        "aff_country_acronym": aff.get("country_code"),
                        "aff_country_name": aff.get("country_name"),
                        "aff_state_text": aff.get("state"),
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
                    author=author,
                    affiliation=affs,
                ),
            )
            raise LoadArticleContribError(e)
    return data


def get_or_create_institution_authors(xmltree, user, item):
    data = []
    authors = ArticleContribs(xmltree=xmltree).contribs
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
                        affiliation = Affiliation.get_or_create(
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
                data.append(obj)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                item=item,
                action="article.xmlsps.get_or_create_institution_authors",
                exception=e,
                exc_traceback=exc_traceback,
                detail=dict(
                    author=author,
                ),
            )
            raise LoadArticleCollabError(e)
    return data


def set_pids(xmltree, article):
    pids = ArticleIds(xmltree=xmltree).data
    if pids.get("v2") or pids.get("v3"):
        article.set_pids(pids)


def set_date_pub(xmltree, article):
    obj_date = ArticleDates(xmltree=xmltree)
    dates = obj_date.article_date or obj_date.collection_date
    article.set_date_pub(dates)


def set_first_last_page_elocation_id(xmltree, article):
    xml = ArticleMetaIssue(xmltree=xmltree)
    article.first_page = xml.fpage
    article.last_page = xml.lpage
    article.elocation_id = xml.elocation_id


def create_or_update_titles(xmltree, user, item):
    titles = ArticleTitles(
        xmltree=xmltree, tags_to_convert_to_html={"bold": "b"}
    ).article_title_list
    data = []
    for title in titles:
        try:
            lang = get_or_create_language(title.get("lang"), user=user)
            if title.get("plain_text") or title.get("html_text"):
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
                    title=title,
                ),
            )
            raise LoadArticleTitleError(e)
    return data


def get_or_create_article_type(xmltree, user):
    article_type = ArticleAndSubArticles(xmltree=xmltree).main_article_type
    return article_type


def get_or_create_issues(xmltree, user, item):
    issue_data = ArticleMetaIssue(xmltree=xmltree).data
    history_dates = ArticleDates(xmltree=xmltree)
    collection_date = history_dates.collection_date or {}
    article_date = history_dates.article_date or {}

    season = collection_date.get("season")
    year = collection_date.get("year") or article_date.get("year")
    month = collection_date.get("month")
    suppl = collection_date.get("suppl")
    try:
        obj = Issue.get_or_create(
            journal=get_journal(xmltree=xmltree),
            number=issue_data.get("number"),
            volume=issue_data.get("volume"),
            season=season,
            year=year,
            month=month,
            supplement=suppl,
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
                issue=issue_data,
            ),
        )
        raise LoadArticleIssueError(e)


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
                funding_name=funding_name,
            ),
        )
        raise LoadArticleSponsorError(e)
