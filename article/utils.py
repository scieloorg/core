from article import models
from issue.models import TocSection

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
from packtools.sps.models.journal_meta import Title as Journal
from packtools.sps.models.kwd_group import KwdGroup


class ArticleSaveError(Exception):
    ...


def get_or_create_doi(xmltree, user):
    doi_with_lang = DoiWithLang(xmltree=xmltree).data
    data = []
    for doi in doi_with_lang:
        obj = models.DOI.get_or_create(
            value=doi.get("value"),
            language=get_or_create_language(doi.get("lang"), user=user),
            creator=user,
        )
        data.append(obj)
    return data


def get_journal(xmltree):
    journal_title = Journal(xmltree=xmltree).journal_title
    try:
        return models.ScieloJournal.objects.get(title=journal_title)
    except models.ScieloJournal.DoesNotExist:
        return None


def get_or_create_fundings(xmltree, user):
    """
    [{'funding-source': ['CNPQ'], 'award-id': ['12345', '67890']},
        {'funding-source': ['FAPESP'], 'award-id': ['23456', '56789']},]
    """

    fundings_group = FundingGroup(xmltree=xmltree).award_groups
    data = []

    for funding_source in fundings_group or []:
        for funding in funding_source.get("funding-source") or []:
            for id in funding_source.get("award-id") or []:
                obj = models.ArticleFunding.get_or_create(
                    award_id=id,
                    funding_source=get_or_create_sponso(funding_name=funding),
                    user=user,
                )
                data.append(obj)
    return data


def get_or_create_toc_sections(xmltree, user):
    toc_sections = ArticleTocSections(xmltree=xmltree).all_section_dict
    data = []
    for key, value in toc_sections.items():
        ## TODO
        ## Criar classmethodod get_or_create??
        obj, create = TocSection.objects.get_or_create(
            plain_text=value,
            language=get_or_create_language(key, user=user),
            creator=user,
        )
        data.append(obj)
    return data


def get_or_create_licenses(xmltree, user):
    licenses = ArticleLicense(xmltree=xmltree).licenses
    data = []
    for license in licenses:
        obj = models.License.get_or_create(
            url=license.get("link"),
            language=get_or_create_language(license.get("lang"), user=user),
            license_p=license.get("license_p"),
            ## TODO
            # Faltando license_type (Alterar no packtools)
            license_type=None,
            creator=user,
        )
        data.append(obj)
    return data


def get_or_create_keywords(xmltree, user):
    kwd_group = KwdGroup(xmltree=xmltree).extract_kwd_data_with_lang_text(subtag=False)

    data = []
    for kwd in kwd_group:
        obj = models.Keyword.get_or_create(
            text=kwd.get("text"),
            language=get_or_create_language(kwd.get("lang"), user=user),
            ## TODO
            ## Verificar relacao keyword com vocabulary
            # vocabulary=None,
            user=user,
        )
        data.append(obj)
    return data


def get_or_create_abstract():
    ## TODO
    ## Dependendo do packtools para extrair os dados do abstract
    pass


def get_or_create_researchers(xmltree, user):
    authors = Authors(xmltree=xmltree).contribs
    # Falta gender e gender_identification_status
    data = []
    for author in authors:
        obj, created = models.Researcher.objects.get_or_create(
            given_names=author.get("given_names"),
            last_name=author.get("surname"),
            orcid=author.get("orcid"),
            suffix=author.get("suffix"),
            lattes=author.get("lattes"),
        )
        data.append(obj)
    return data


def set_pids(xmltree, article):
    pids = ArticleIds(xmltree=xmltree).data
    if pids.get("v2") or pids.get("v3"):
        article.set_pids(pids)


def set_date_pub(xmltree, article):
    dates = ArticleDates(xmltree=xmltree).article_date
    article.set_date_pub(dates)


def set_first_last_page(xmltree, article):
    article.first_page = ArticleMetaIssue(xmltree=xmltree).fpage
    article.last_page = ArticleMetaIssue(xmltree=xmltree).lpage


def set_elocation_id(xmltree, article):
    article.elocation_id = ArticleMetaIssue(xmltree=xmltree).elocation_id


def get_or_create_titles(xmltree, user):
    titles = ArticleTitles(xmltree=xmltree).article_title_list
    data = []
    for title in titles:
        format_title = " ".join(title.get("text", "").split())
        ## TODO
        ## Criar get_or_create para DocumentTitle
        obj, created = models.DocumentTitle.objects.get_or_create(
            plain_text=format_title,
            rich_text=title.get("text"),
            language=get_or_create_language(title.get("lang"), user=user)
            if xmltree
            else None,
            creator=user,
        )
        data.append(obj)
    return data


def get_or_create_article_type(xmltree, user):
    article_type = ArticleAndSubArticles(xmltree=xmltree).main_article_type
    obj, created = models.ArticleType.objects.get_or_create(text=article_type)
    return obj


def get_or_create_issues(xmltree, user):
    issue_data = ArticleMetaIssue(xmltree=xmltree).data
    collection_date = ArticleDates(xmltree=xmltree).collection_date
    obj = models.Issue.get_or_create(
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


def get_or_create_language(lang, user):
    obj = models.Language.get_or_create(code2=lang, creator=user)
    return obj


def get_or_create_main_language(xmltree, user):
    lang = ArticleAndSubArticles(xmltree=xmltree).main_lang
    obj = get_or_create_language(lang, user)
    return obj


def get_or_create_sponso(funding_name):
    obj = models.Sponsor.get_or_create(
        inst_name=funding_name,
        inst_acronym=None,
        level_1=None,
        level_2=None,
        level_3=None,
        location=None,
        official=None,
        is_official=None,
    )
    return obj
