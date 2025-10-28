import logging
import sys
import traceback
from datetime import datetime
from itertools import product

from django.utils.translation import gettext_lazy as _
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
from article.models import Article, ArticleFunding, DocumentAbstract, DocumentTitle
from core.models import Language
from core.utils.extracts_normalized_email import extracts_normalized_email
from doi.models import DOI
from institution.models import Sponsor
from issue.models import Issue, TocSection
from journal.models import Journal
from location.models import Location
from pid_provider.choices import PPXML_STATUS_DONE, PPXML_STATUS_INVALID
from pid_provider.models import PidProviderXML
from researcher.models import Affiliation, InstitutionalAuthor, Researcher
from tracker.models import UnexpectedEvent
from vocabulary.models import Keyword


def add_error(errors, function_name, error, **kwargs):
    """
    Helper para adicionar erros de forma padronizada.

    Args:
        errors: Lista de erros para adicionar o novo erro
        function_name: Nome da função onde o erro ocorreu
        error: Objeto Exception capturado
        **kwargs: Parâmetros adicionais para contexto do erro
    """
    error_dict = {
        "function": function_name,
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "timestamp": datetime.now().isoformat(),
    }
    error_dict.update(kwargs)
    errors.append(error_dict)


def load_article(user, xml=None, file_path=None, v3=None, pp_xml=None):
    """
    Carrega um artigo a partir de XML.

    Este método processa um arquivo XML de artigo científico e cria/atualiza
    todos os objetos relacionados no banco de dados, incluindo metadados,
    autores, afiliações, resumos, palavras-chave, etc.

    Args:
        user: Usuário responsável pela operação (obrigatório)
        xml: String contendo o XML do artigo (opcional)
        file_path: Caminho para o arquivo XML (opcional)
        v3: PID v3 do artigo (opcional)
        pp_xml: Objeto PidProviderXML relacionado (opcional)

    Returns:
        Article: Instância do artigo processado com todos os relacionamentos
                criados. Retorna None se não foi possível processar.

    Raises:
        ValueError: Se nenhuma fonte de dados (xml, file_path ou v3) for fornecida
                   ou se o usuário não for informado

    Note:
        - Erros durante o processamento são coletados em article.errors
        - O processamento continua mesmo com falhas parciais
        - O campo article.valid indica se o processamento foi completo
    """
    logging.info(f"load article {pp_xml} {v3} {file_path}")
    errors = []
    article = None  # Inicializar no início

    # Validações iniciais
    if not user:
        raise ValueError("User is required")

    if not any([pp_xml, v3, file_path, xml]):
        raise ValueError(
            "load_article() requires params: pp_xml or v3 or file_path or xml"
        )

    try:
        if pp_xml:
            xml_with_pre = pp_xml.xml_with_pre
        elif v3:
            pp_xml = PidProviderXML.objects.get(v3=v3)
            xml_with_pre = pp_xml.xml_with_pre
        elif file_path:
            for xml_with_pre in XMLWithPre.create(file_path):
                xmltree = xml_with_pre.xmltree
                break
        elif xml:
            xml_with_pre = XMLWithPre("", etree.fromstring(xml))
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            item=str(pp_xml or v3 or file_path or "xml"),
            action="article.sources.xmlsps.load_article",
            exception=e,
            exc_traceback=exc_traceback,
            detail=dict(
                function="article.sources.xmlsps.load_article",
                xml=f"{xml}",
                v3=v3,
                file_path=file_path,
                pp_xml=str(pp_xml),
            ),
        )
        item = str(pp_xml or v3 or file_path or "xml")
        if pp_xml:
            pp_xml.proc_status = PPXML_STATUS_INVALID
            pp_xml.save()
            updated = (
                Article.objects.filter(pid_v3=pp_xml.v3)
                .exclude(
                    pp_xml=pp_xml,
                    data_status=choices.DATA_STATUS_INVALID,
                )
                .update(
                    pp_xml=pp_xml,
                    data_status=choices.DATA_STATUS_INVALID,
                )
            )
        raise ValueError(f"Unable to get XML to load article from {item}: {e}")

    pid_v3 = v3 or xml_with_pre.v3

    try:
        # Sequência organizada para atribuição de campos do Article
        # Do mais simples (campos diretos) para o mais complexo (FKs e M2M)
        event = None
        xmltree = xml_with_pre.xmltree

        logging.info(f"Article {pid_v3} {xml_with_pre.sps_pkg_name}")

        # CRIAÇÃO/OBTENÇÃO DO OBJETO PRINCIPAL
        article = Article.create_or_update(
            user=user,
            pid_v3=pid_v3,
            sps_pkg_name=xml_with_pre.sps_pkg_name,
        )
        logging.info(f"...Article {pid_v3} {xml_with_pre.sps_pkg_name}")

        article.events.all().delete()
        event = article.add_event(user, _("load article"))
        # Configurar todos os campos antes de salvar (Sugestão 9)
        article.valid = False
        article.data_status = choices.DATA_STATUS_PENDING
        article.pp_xml = pp_xml
        article.sps_pkg_name = xml_with_pre.sps_pkg_name

        # CAMPOS SIMPLES EXTRAÍDOS DO XML
        set_pids(xmltree=xmltree, article=article, errors=errors)
        set_date_pub(xmltree=xmltree, article=article, errors=errors)
        set_license(xmltree=xmltree, article=article, errors=errors)
        set_first_last_page_elocation_id(
            xmltree=xmltree, article=article, errors=errors
        )
        article.article_type = get_or_create_article_type(
            xmltree=xmltree, user=user, errors=errors
        )

        # FOREIGN KEYS SIMPLES
        article.journal = get_journal(xmltree=xmltree, errors=errors)
        article.issue = get_or_create_issues(
            xmltree=xmltree,
            user=user,
            journal=article.journal,
            item=pid_v3,
            errors=errors,
        )

        # Salvar uma vez após definir todos os campos simples
        logging.info(
            f"Saving article {article.pid_v3} {xml_with_pre.sps_pkg_name} {xml_with_pre.main_doi}"
        )

        article.save()

        # MANY-TO-MANY (requerem que o objeto esteja salvo)
        main_lang = get_or_create_main_language(
            xmltree=xmltree, user=user, errors=errors
        )
        if main_lang:
            article.languages.add(main_lang)

        article.toc_sections.set(
            get_or_create_toc_sections(xmltree=xmltree, user=user, errors=errors)
        )
        article.titles.set(
            create_or_update_titles(
                xmltree=xmltree, user=user, item=pid_v3, errors=errors
            )
        )
        article.abstracts.set(
            create_or_update_abstract(
                xmltree=xmltree, user=user, article=article, item=pid_v3, errors=errors
            )
        )
        article.keywords.set(
            create_or_update_keywords(
                xmltree=xmltree, user=user, item=pid_v3, errors=errors
            )
        )
        article.researchers.set(
            create_or_update_researchers(
                xmltree=xmltree, user=user, item=pid_v3, errors=errors
            )
        )
        article.collab.set(
            get_or_create_institution_authors(
                xmltree=xmltree, user=user, item=pid_v3, errors=errors
            )
        )
        article.fundings.set(
            get_or_create_fundings(
                xmltree=xmltree, user=user, item=pid_v3, errors=errors
            )
        )
        article.doi.set(get_or_create_doi(xmltree=xmltree, user=user, errors=errors))
        article.create_legacy_keys(user)
        if not article.pid_v2:
            add_error(errors, "load_article", "Article has no PID v2", item=article.pid_v3)
        if not errors:
            article.mark_as_completed()

        event.finish(completed=not errors, errors=errors)
        logging.info(
            f"The article {pid_v3} has been processed with {len(errors)} errors"
        )
        return article
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()

        if event:
            event.finish(errors=errors, exceptions=traceback.format_exc())
            raise
        UnexpectedEvent.create(
            item=str(pp_xml or v3 or file_path or "xml"),
            action="article.sources.xmlsps.load_article",
            exception=e,
            exc_traceback=exc_traceback,
            detail=dict(
                function="article.sources.xmlsps.load_article",
                xml=f"{xml}",
                v3=v3,
                file_path=file_path,
                pp_xml=str(pp_xml),
            ),
        )
        raise


def get_or_create_doi(xmltree, user, errors):
    """
    Extrai e cria objetos DOI a partir do XML.

    Args:
        xmltree: Árvore XML do artigo
        user: Usuário criador
        errors: Lista para coletar erros

    Returns:
        list: Lista de objetos DOI criados
    """
    data = []
    try:
        doi_with_lang = DoiWithLang(xmltree=xmltree).data
        for doi in doi_with_lang:
            if not doi.get("value"):
                continue
            try:
                lang = get_or_create_language(doi.get("lang"), user=user, errors=errors)
                obj = DOI.get_or_create(
                    value=doi.get("value"),
                    language=lang,
                    creator=user,
                )
                data.append(obj)
            except Exception as e:
                add_error(errors, "get_or_create_doi", e, item=doi)
    except Exception as e:
        add_error(errors, "get_or_create_doi", e)
    return data


def get_journal(xmltree, errors):
    """
    Obtém o journal a partir do XML.

    Tenta primeiro pelo título, depois pelo ISSN.

    Args:
        xmltree: Árvore XML do artigo
        errors: Lista para coletar erros

    Returns:
        Journal: Objeto Journal ou None se não encontrado
    """
    try:
        return Journal.objects.get(title=Title(xmltree=xmltree).journal_title)
    except (Journal.DoesNotExist, Journal.MultipleObjectsReturned):
        pass
    except Exception as e:
        add_error(errors, "get_journal", e)

    try:
        issn = ISSN(xmltree=xmltree)
        return Journal.get(
            issn_electronic=issn.epub,
            issn_print=issn.ppub,
        )
    except Journal.DoesNotExist:
        return None
    except Exception as e:
        add_error(errors, "get_journal", e)
        return None


def get_or_create_fundings(xmltree, user, item, errors):
    """
    Extrai e cria objetos de financiamento a partir do XML.

    Processa funding-source e award-id em combinações para criar
    objetos ArticleFunding com seus respectivos sponsors.

    Args:
        xmltree: Árvore XML do artigo
        user: Usuário criador
        item: Identificador do item (para log)
        errors: Lista para coletar erros

    Returns:
        list: Lista de objetos ArticleFunding criados

    Example:
        fundings_award_group:
        [{
            'funding-source': ['São Paulo Research Foundation', 'CAPES', 'CNPq'],
            'award-id': ['2009/53363-8, 2009/52807-0, 2009/51766-8']
        }]
    """
    data = []
    try:
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
                        sponsor = create_or_update_sponsor(
                            funding_name=fs, user=user, item=item, errors=errors
                        )
                        if sponsor:
                            obj = ArticleFunding.get_or_create(
                                award_id=award_id,
                                funding_source=sponsor,
                                user=user,
                            )
                            if obj:
                                data.append(obj)
                    except Exception as e:
                        add_error(
                            errors, "get_or_create_fundings", e, item=item, data=result
                        )
    except Exception as e:
        add_error(errors, "get_or_create_fundings", e, item=item)
    return data


def get_or_create_toc_sections(xmltree, user, errors):
    """
    Extrai e cria seções do sumário (TOC) a partir do XML.

    Args:
        xmltree: Árvore XML do artigo
        user: Usuário criador
        errors: Lista para coletar erros

    Returns:
        list: Lista de objetos TocSection criados
    """
    data = []
    try:
        toc_sections = ArticleTocSections(xmltree=xmltree).sections
        for item in toc_sections:
            section_title = item.get("section")

            if not section_title:
                continue

            section_lang = item.get("parent_lang")
            try:
                lang = get_or_create_language(section_lang, user=user, errors=errors)
                obj = TocSection.get_or_create(
                    value=section_title,
                    language=lang,
                    user=user,
                )
                data.append(obj)
            except Exception as e:
                add_error(errors, "get_or_create_toc_sections", e, item=item)
    except Exception as e:
        add_error(errors, "get_or_create_toc_sections", e)
    return data


def set_license(xmltree, article, errors):
    """
    Define a licença do artigo a partir do XML.

    Args:
        xmltree: Árvore XML do artigo
        article: Objeto Article para atualizar
        errors: Lista para coletar erros
    """
    try:
        xml_licenses = ArticleLicense(xmltree=xmltree).licenses
        for xml_license in xml_licenses:
            if license := xml_license.get("link"):
                article.article_license = license
    except Exception as e:
        add_error(errors, "set_license", e)


def create_or_update_keywords(xmltree, user, item, errors):
    """
    Extrai e cria palavras-chave a partir do XML.

    Args:
        xmltree: Árvore XML do artigo
        user: Usuário criador
        item: Identificador do item (para log)
        errors: Lista para coletar erros

    Returns:
        list: Lista de objetos Keyword criados
    """
    data = []
    try:
        article_keywords = ArticleKeywords(xmltree=xmltree)
        article_keywords.configure(tags_to_convert_to_html={"bold": "b"})

        for kwd in article_keywords.items:
            try:
                lang = get_or_create_language(kwd.get("lang"), user=user, errors=errors)
                obj = Keyword.create_or_update(
                    user=user,
                    vocabulary=None,
                    language=lang,
                    text=kwd.get("plain_text"),
                    html_text=kwd.get("html_text"),
                )
                data.append(obj)
            except Exception as e:
                add_error(errors, "create_or_update_keywords", e, item=item, data=kwd)
    except Exception as e:
        add_error(errors, "create_or_update_keywords", e, item=item)
    return data


def create_or_update_abstract(xmltree, user, article, item, errors):
    """
    Extrai e cria resumos do artigo a partir do XML.

    Args:
        xmltree: Árvore XML do artigo
        user: Usuário criador
        article: Objeto Article relacionado
        item: Identificador do item (para log)
        errors: Lista para coletar erros

    Returns:
        list: Lista de objetos DocumentAbstract criados
    """
    data = []
    try:
        abstract = ArticleAbstract(xmltree=xmltree)
        abstract.configure(tags_to_convert_to_html={"bold": "b", "italic": "i"})

        if xmltree.find(".//abstract") is not None:
            for ab in abstract.get_abstracts():
                if not ab:
                    continue
                try:
                    lang = get_or_create_language(
                        ab.get("lang"), user=user, errors=errors
                    )
                    obj = DocumentAbstract.create_or_update(
                        user=user,
                        article=article,
                        language=lang,
                        text=ab.get("plain_text"),
                        rich_text=ab.get("html_text"),
                    )
                    data.append(obj)
                except Exception as e:
                    add_error(
                        errors, "create_or_update_abstract", e, item=item, data=ab
                    )
    except Exception as e:
        add_error(errors, "create_or_update_abstract", e, item=item)
    return data


def create_or_update_researchers(xmltree, user, item, errors):
    """
    Extrai e cria pesquisadores/autores a partir do XML.

    Processa informações de autores incluindo nomes, ORCID, Lattes,
    afiliações e emails.

    Args:
        xmltree: Árvore XML do artigo
        user: Usuário criador
        item: Identificador do item (para log)
        errors: Lista para coletar erros

    Returns:
        list: Lista de objetos Researcher criados
    """
    article_lang = None
    try:
        article_lang = ArticleAndSubArticles(xmltree=xmltree).main_lang
    except Exception as e:
        add_error(errors, "create_or_update_researchers.get_main_lang", e)

    data = []
    try:
        authors = XMLContribs(xmltree=xmltree).contribs

        for author in authors:
            try:
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
                add_error(
                    errors,
                    "create_or_update_researchers",
                    e,
                    item=item,
                    author=author,
                    affiliation=author.get("affs", []),
                )
    except Exception as e:
        add_error(errors, "create_or_update_researchers", e, item=item)
    return data


def get_or_create_institution_authors(xmltree, user, item, errors):
    """
    Extrai e cria autores institucionais (colaborações) a partir do XML.

    Args:
        xmltree: Árvore XML do artigo
        user: Usuário criador
        item: Identificador do item (para log)
        errors: Lista para coletar erros

    Returns:
        list: Lista de objetos InstitutionalAuthor criados
    """
    data = []
    try:
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
                add_error(
                    errors,
                    "get_or_create_institution_authors",
                    e,
                    item=item,
                    author=author,
                )
    except Exception as e:
        add_error(errors, "get_or_create_institution_authors", e, item=item)
    return data


def set_pids(xmltree, article, errors):
    """
    Define os PIDs (identificadores persistentes) do artigo.

    Args:
        xmltree: Árvore XML do artigo
        article: Objeto Article para atualizar
        errors: Lista para coletar erros
    """
    try:
        pids = ArticleIds(xmltree=xmltree).data
        if pids.get("v2") or pids.get("v3"):
            article.set_pids(pids)
    except Exception as e:
        add_error(errors, "set_pids", e)


def set_date_pub(xmltree, article, errors):
    """
    Define as datas de publicação do artigo.

    Args:
        xmltree: Árvore XML do artigo
        article: Objeto Article para atualizar
        errors: Lista para coletar erros
    """
    try:
        obj_date = ArticleDates(xmltree=xmltree)
        dates = obj_date.article_date or obj_date.collection_date
        article.set_date_pub(dates)
    except Exception as e:
        add_error(errors, "set_date_pub", e)


def set_first_last_page_elocation_id(xmltree, article, errors):
    """
    Define paginação e elocation-id do artigo.

    Args:
        xmltree: Árvore XML do artigo
        article: Objeto Article para atualizar
        errors: Lista para coletar erros
    """
    try:
        xml = ArticleMetaIssue(xmltree=xmltree)
        article.first_page = xml.fpage
        article.last_page = xml.lpage
        article.elocation_id = xml.elocation_id
    except Exception as e:
        add_error(errors, "set_first_last_page_elocation_id", e)


def create_or_update_titles(xmltree, user, item, errors):
    """
    Extrai e cria títulos do artigo a partir do XML.

    Args:
        xmltree: Árvore XML do artigo
        user: Usuário criador
        item: Identificador do item (para log)
        errors: Lista para coletar erros

    Returns:
        list: Lista de objetos DocumentTitle criados
    """
    data = []
    try:
        titles = ArticleTitles(
            xmltree=xmltree, tags_to_convert_to_html={"bold": "b"}
        ).article_title_list

        for title in titles:
            try:
                lang = get_or_create_language(
                    title.get("lang"), user=user, errors=errors
                )
                if title.get("plain_text") or title.get("html_text"):
                    obj = DocumentTitle.create_or_update(
                        title=title.get("plain_text"),
                        rich_text=title.get("html_text"),
                        language=lang,
                        user=user,
                    )
                    data.append(obj)
            except Exception as e:
                add_error(errors, "create_or_update_titles", e, item=item, title=title)
    except Exception as e:
        add_error(errors, "create_or_update_titles", e, item=item)
    return data


def get_or_create_article_type(xmltree, user, errors):
    """
    Obtém o tipo de artigo a partir do XML.

    Args:
        xmltree: Árvore XML do artigo
        user: Usuário (não utilizado atualmente)
        errors: Lista para coletar erros

    Returns:
        str: Tipo do artigo ou None se houver erro
    """
    try:
        article_type = ArticleAndSubArticles(xmltree=xmltree).main_article_type
        return article_type
    except Exception as e:
        add_error(errors, "get_or_create_article_type", e)
        return None


def get_or_create_issues(xmltree, user, journal, item, errors):
    """
    Extrai e cria o fascículo (issue) a partir do XML.

    Args:
        xmltree: Árvore XML do artigo
        user: Usuário criador
        journal: Objeto Journal relacionado
        item: Identificador do item (para log)
        errors: Lista para coletar erros

    Returns:
        Issue: Objeto Issue criado ou None se houver erro
    """
    try:
        issue_data = ArticleMetaIssue(xmltree=xmltree).data
        history_dates = ArticleDates(xmltree=xmltree)
        collection_date = history_dates.collection_date or {}
        article_date = history_dates.article_date or {}

        season = collection_date.get("season")
        year = collection_date.get("year") or article_date.get("year")
        month = collection_date.get("month")
        suppl = collection_date.get("suppl")

        obj = Issue.get_or_create(
            journal=journal,
            number=issue_data.get("number"),
            volume=issue_data.get("volume"),
            season=season,
            year=year,
            month=month,
            supplement=suppl,
            user=user,
        )
        return obj
    except Exception as e:
        add_error(
            errors,
            "get_or_create_issues",
            e,
            item=item,
            issue=issue_data if "issue_data" in locals() else None,
        )
        return None


def get_or_create_language(lang, user, errors):
    """
    Obtém ou cria um objeto Language.

    Args:
        lang: Código do idioma (ISO 639-1)
        user: Usuário criador
        errors: Lista para coletar erros

    Returns:
        Language: Objeto Language ou None se houver erro
    """
    try:
        obj = Language.get_or_create(code2=lang, creator=user)
        return obj
    except Exception as e:
        add_error(errors, "get_or_create_language", e, lang=lang)
        return None


def get_or_create_main_language(xmltree, user, errors):
    """
    Obtém o idioma principal do artigo.

    Args:
        xmltree: Árvore XML do artigo
        user: Usuário criador
        errors: Lista para coletar erros

    Returns:
        Language: Objeto Language do idioma principal ou None se houver erro
    """
    try:
        lang = ArticleAndSubArticles(xmltree=xmltree).main_lang
        obj = get_or_create_language(lang, user, errors)
        return obj
    except Exception as e:
        add_error(errors, "get_or_create_main_language", e)
        return None


def create_or_update_sponsor(funding_name, user, item, errors):
    """
    Cria ou atualiza um patrocinador/financiador.

    Args:
        funding_name: Nome do financiador
        user: Usuário criador
        item: Identificador do item (para log)
        errors: Lista para coletar erros

    Returns:
        Sponsor: Objeto Sponsor criado ou None se houver erro
    """
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
        add_error(
            errors, "create_or_update_sponsor", e, item=item, funding_name=funding_name
        )
        return None
