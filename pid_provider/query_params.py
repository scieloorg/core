from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from core.utils.profiling_tools import profile_function
from pid_provider import exceptions


@profile_function
def get_valid_query_parameters(xml_adapter):
    return get_journal_q_expression(xml_adapter), list(get_kwargs(xml_adapter))


@profile_function
def get_kwargs(xml_adapter):
    """
    Gera parâmetros de consulta válidos para pesquisa no banco de dados com base nos dados do adaptador XML.

    Esta função constrói expressões Q do Django para filtragem por periódico e ano de publicação,
    e gera conjuntos de parâmetros para diferentes cenários de consulta (AOP vs. artigos regulares).

    Args:
        xml_adapter: Objeto adaptador XML contendo metadados do artigo, incluindo informações do periódico,
                     datas de publicação e detalhes do artigo.

    Returns:
        tuple: Uma tupla contendo:
            - q (django.db.models.Q): Expressão Q combinada para filtragem por periódico e ano de publicação.
            - kwargs (list): Lista de dicionários contendo parâmetros de consulta válidos para diferentes cenários.

    Raises:
        RequiredISSNErrorToGetPidProviderXMLError: Se nenhum ISSN for fornecido.
        RequiredPublicationYearErrorToGetPidProviderXMLError: Se nenhum ano de publicação for fornecido.
        NotEnoughParametersToGetPidProviderXMLError: Se os parâmetros de desambiguação forem insuficientes.
    """
    basic_params = get_basic_params(xml_adapter)
    if xml_adapter.is_aop:
        yield _get_valid_params(xml_adapter, basic_params)
    else:
        params = get_issue_params(xml_adapter, filter_by_issue=True) or {}
        params.update(basic_params)
        yield _get_valid_params(xml_adapter, params)

        params = get_issue_params(xml_adapter, aop_version=True) or {}
        params.update(basic_params)
        yield _get_valid_params(xml_adapter, params)


@profile_function
def _get_valid_params(xml_adapter, params):
    """
    Cria um dicionário de parâmetros validado combinando parâmetros básicos e de fascículo.

    Esta função interna mescla parâmetros básicos do artigo com parâmetros específicos do fascículo
    e os valida. Se a validação falhar devido à falta de informações do autor, ela tenta
    adicionar parâmetros de desambiguação.

    Args:
        xml_adapter: Objeto adaptador XML contendo metadados do artigo.
        basic_params (dict): Dicionário de parâmetros de consulta básicos.
        issue_params (dict, optional): Dicionário de parâmetros específicos do fascículo. Padrão para None.

    Returns:
        dict: Dicionário de parâmetros combinado e validado.

    Raises:
        NotEnoughParametersToGetPidProviderXMLError: Se os parâmetros de desambiguação forem insuficientes.
    """
    try:
        validate_query_params(params)
    except exceptions.RequiredAuthorErrorToGetPidProviderXMLError:
        try:
            params.update(get_disambiguation_params(xml_adapter))
        except exceptions.NotEnoughParametersToGetPidProviderXMLError:
            raise
    return params


@profile_function
def get_journal_q_expression(xml_adapter):
    """
    Cria uma expressão Q do Django para identificação de periódico usando valores de ISSN.

    Esta função constrói uma expressão Q que corresponde a artigos por ISSN eletrônico
    ou ISSN impresso. Pelo menos um ISSN deve ser fornecido.

    Args:
        xml_adapter: Objeto adaptador XML contendo informações de ISSN do periódico.

    Returns:
        django.db.models.Q: Expressão Q para filtragem de periódico.

    Raises:
        RequiredISSNErrorToGetPidProviderXMLError: Se nem o ISSN eletrônico nem o impresso forem fornecidos.
    """
    if xml_adapter.journal_issn_electronic and xml_adapter.journal_issn_print:
        return Q(issn_electronic=xml_adapter.journal_issn_electronic) | Q(
            issn_print=xml_adapter.journal_issn_print
        )

    if xml_adapter.journal_issn_electronic:
        return Q(issn_electronic=xml_adapter.journal_issn_electronic)

    if xml_adapter.journal_issn_print:
        return Q(issn_print=xml_adapter.journal_issn_print)

    raise exceptions.RequiredISSNErrorToGetPidProviderXMLError(
        _("Required Print or Electronic ISSN to identify XML {}").format(
            xml_adapter.pkg_name,
        )
    )


@profile_function
def get_pub_year_expression(xml_adapter):
    """
    Cria uma expressão Q do Django para filtragem por ano de publicação.

    Esta função constrói uma expressão Q que corresponde a artigos por ano de publicação
    do artigo ou ano de publicação geral. Pelo menos um ano deve ser fornecido.

    Args:
        xml_adapter: Objeto adaptador XML contendo informações de ano de publicação.

    Returns:
        django.db.models.Q: Expressão Q para filtragem por ano de publicação.

    Raises:
        RequiredPublicationYearErrorToGetPidProviderXMLError: Se nenhum ano de publicação for fornecido.
    """
    if xml_adapter.pub_year:
        return {"pub_year": xml_adapter.pub_year}

    raise exceptions.RequiredPublicationYearErrorToGetPidProviderXMLError(
        _("Required issue or article publication year {}").format(
            xml_adapter.pkg_name,
        )
    )


@profile_function
def get_basic_params(xml_adapter):
    """
    Extrai parâmetros de consulta básicos do adaptador XML para identificação do artigo.

    Esta função recupera identificadores fundamentais do artigo, incluindo sobrenomes dos autores,
    colaborações, DOI e ID de localização eletrônica do adaptador XML.

    Args:
        xml_adapter: Objeto adaptador XML contendo metadados básicos do artigo.

    Returns:
        dict: Dicionário de parâmetros de consulta básicos, incluindo:
            - z_surnames: Sobrenomes dos autores.
            - z_collab: Informações de colaboração.
            - main_doi__iexact: DOI principal (correspondência exata sem distinção entre maiúsculas e minúsculas).
            - elocation_id__iexact: ID de localização eletrônica (correspondência exata sem distinção entre maiúsculas e minúsculas).
    """
    _params = get_pub_year_expression(xml_adapter)
    if xml_adapter.z_surnames:
        _params["z_surnames"] = xml_adapter.z_surnames
    if xml_adapter.z_collab:
        _params["z_collab"] = xml_adapter.z_collab
    if xml_adapter.main_doi:
        _params["main_doi__iexact"] = xml_adapter.main_doi
    if xml_adapter.elocation_id:
        _params["elocation_id__iexact"] = xml_adapter.elocation_id
    return _params


@profile_function
def get_issue_params(xml_adapter, filter_by_issue=False, aop_version=False):
    """
    Extrai parâmetros de consulta específicos do fascículo do adaptador XML.

    Esta função recupera parâmetros relacionados ao fascículo, como volume, número, suplemento
    e informações de página. O comportamento muda dependendo se é para artigos AOP (Ahead of Print)
    ou artigos regulares baseados em fascículos.

    Args:
        xml_adapter: Objeto adaptador XML contendo metadados do fascículo.
        filter_by_issue (bool, optional): Se True, inclui parâmetros específicos do fascículo
                                         como volume, número e informações de página. Padrão para False.
        aop_version (bool, optional): Se True, define restrições nulas para artigos AOP
                                     (sem volume, número ou suplemento). Padrão para False.

    Returns:
        dict: Dicionário de parâmetros de consulta específicos do fascículo. Para a versão AOP, inclui
              restrições nulas; para filtragem por fascículo, inclui parâmetros de correspondência exata.
    """
    _params = {}
    if aop_version:
        _params["volume__isnull"] = True
        _params["number__isnull"] = True
        _params["suppl__isnull"] = True
    elif filter_by_issue:
        _params["volume__iexact"] = xml_adapter.volume
        _params["number__iexact"] = xml_adapter.number
        _params["suppl__iexact"] = xml_adapter.suppl

        if xml_adapter.fpage:
            try:
                if int(xml_adapter.fpage) == 0:
                    fpage = None
                else:
                    fpage = xml_adapter.fpage
            except (TypeError, ValueError):
                fpage = None
            if fpage:
                _params["fpage__iexact"] = fpage
                _params["fpage_seq__iexact"] = xml_adapter.fpage_seq
                _params["lpage__iexact"] = xml_adapter.lpage
    return _params


@profile_function
def get_disambiguation_params(xml_adapter):
    """
    Extrai parâmetros de desambiguação para identificação do artigo quando os parâmetros básicos são insuficientes.

    Esta função fornece parâmetros adicionais (links ou conteúdo parcial do corpo) que podem ser usados
    para desambiguar artigos quando os identificadores padrão não são suficientes para uma identificação única.

    Args:
        xml_adapter: Objeto adaptador XML contendo dados de desambiguação.

    Returns:
        dict: Dicionário contendo parâmetros de desambiguação (z_links ou z_partial_body).

    Raises:
        NotEnoughParametersToGetPidProviderXMLError: Se nem links nem conteúdo parcial do corpo
                                                     estiverem disponíveis para desambiguação.
    """
    if xml_adapter.z_links:
        return {"z_links": xml_adapter.z_links}

    if xml_adapter.z_partial_body:
        return {"z_partial_body": xml_adapter.z_partial_body}

    raise exceptions.NotEnoughParametersToGetPidProviderXMLError(
        _("No attribute enough for disambiguations {}").format(
            xml_adapter.pkg_name,
        )
    )


@profile_function
def validate_query_params(query_params):
    """
    Valida se os parâmetros de consulta contêm informações suficientes para identificação do artigo.

    Esta função garante que os parâmetros fornecidos incluam identificadores fortes
    (DOI, primeira página ou ID de localização eletrônica) ou informações do autor
    (sobrenomes ou colaboração).

    Args:
        query_params (dict): Dicionário de parâmetros de consulta a serem validados.

    Returns:
        bool: True se a validação for bem-sucedida.

    Raises:
        RequiredAuthorErrorToGetPidProviderXMLError: Se nenhuma informação do autor for fornecida
                                                     e nenhum identificador forte estiver disponível.
    """
    if any(
        [
            query_params.get("main_doi__iexact"),
            query_params.get("fpage__iexact"),
            query_params.get("elocation_id__iexact"),
        ]
    ):
        return True

    if any(
        [
            query_params.get("z_surnames"),
            query_params.get("z_collab"),
        ]
    ):
        return True

    raise exceptions.RequiredAuthorErrorToGetPidProviderXMLError(
        _("Required collab or surname {}").format(
            query_params,
        )
    )
