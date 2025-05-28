from django.db.models import Q
from django.utils.translation import gettext as _

from pid_provider import exceptions


def get_valid_query_parameters(xml_adapter):
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
    q = (get_journal_q_expression(xml_adapter)) & (get_pub_year_expression(xml_adapter))

    basic_params = get_basic_params(xml_adapter)
    if xml_adapter.is_aop:
        kwargs = [_get_valid_params(xml_adapter, basic_params)]
    else:
        kwargs = [
            _get_valid_params(
                xml_adapter,
                basic_params,
                get_issue_params(xml_adapter, filter_by_issue=True),
            ),
            _get_valid_params(
                xml_adapter,
                basic_params,
                get_issue_params(xml_adapter, aop_version=True),
            ),
        ]
    return q, kwargs


def _get_valid_params(xml_adapter, basic_params, issue_params=None):
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
    valid_params = {}
    valid_params.update(basic_params)
    if issue_params:
        valid_params.update(issue_params)
    try:
        validate_query_params(valid_params)
    except exceptions.RequiredAuthorErrorToGetPidProviderXMLError:
        try:
            disambiguation_params = get_disambiguation_params(xml_adapter)
            valid_params.update(disambiguation_params)
        except exceptions.NotEnoughParametersToGetPidProviderXMLError:
            raise
    return valid_params


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
    q = Q()
    if xml_adapter.journal_issn_electronic:
        q |= Q(issn_electronic=xml_adapter.journal_issn_electronic)
    if xml_adapter.journal_issn_print:
        q |= Q(issn_print=xml_adapter.journal_issn_print)
    if not xml_adapter.journal_issn_electronic and not xml_adapter.journal_issn_print:
        raise exceptions.RequiredISSNErrorToGetPidProviderXMLError(
            _("Required Print or Electronic ISSN to identify XML {}").format(
                xml_adapter.pkg_name,
            )
        )
    return q


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
    q = Q()
    if xml_adapter.article_pub_year:
        q |= Q(article_pub_year=xml_adapter.article_pub_year)
    if xml_adapter.pub_year:
        q |= Q(pub_year=xml_adapter.pub_year)
    if not xml_adapter.article_pub_year and not xml_adapter.pub_year:
        raise exceptions.RequiredPublicationYearErrorToGetPidProviderXMLError(
            _("Required issue or article publication year {}").format(
                xml_adapter.pkg_name,
            )
        )
    return q


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
    _params = dict(
        z_surnames=xml_adapter.z_surnames or None,
        z_collab=xml_adapter.z_collab or None,
    )
    if xml_adapter.main_doi:
        _params["main_doi__iexact"] = xml_adapter.main_doi
    _params["elocation_id__iexact"] = xml_adapter.elocation_id
    return _params


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
        _params["fpage__iexact"] = xml_adapter.fpage
        _params["fpage_seq__iexact"] = xml_adapter.fpage_seq
        _params["lpage__iexact"] = xml_adapter.lpage
    return _params


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
    _params = {}
    if xml_adapter.z_links:
        _params["z_links"] = xml_adapter.z_links
    elif xml_adapter.z_partial_body:
        _params["z_partial_body"] = xml_adapter.z_partial_body
    else:
        raise exceptions.NotEnoughParametersToGetPidProviderXMLError(
            _("No attribute enough for disambiguations {}").format(
                _params,
            )
        )
    return _params


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
    _params = query_params

    if any(
        [
            _params.get("main_doi__iexact"),
            _params.get("fpage__iexact"),
            _params.get("elocation_id__iexact"),
        ]
    ):
        return True

    if not any(
        [
            _params.get("z_surnames"),
            _params.get("z_collab"),
        ]
    ):
        raise exceptions.RequiredAuthorErrorToGetPidProviderXMLError(
            _("Required collab or surname {}").format(
                _params,
            )
        )
    return True


def get_xml_adapter_data(xml_adapter):
    """
    Extrai todos os dados relevantes do objeto adaptador XML em um formato padronizado.

    Esta função tenta recuperar dados do atributo 'data' do adaptador primeiro,
    e retorna para a extração de atributos individuais se o atributo 'data' não existir.
    Isso fornece uma interface consistente para acessar informações do adaptador XML.

    Args:
        xml_adapter: Objeto adaptador XML contendo metadados do artigo e do periódico.

    Returns:
        dict: Dicionário contendo todos os dados relevantes do adaptador, incluindo:
            - pkg_name: Nome do pacote.
            - issn_print/issn_electronic: Valores de ISSN do periódico.
            - article_pub_year/pub_year: Anos de publicação.
            - main_doi: DOI principal.
            - elocation_id: ID de localização eletrônica.
            - volume/number/suppl: Informações do fascículo.
            - fpage/fpage_seq/lpage: Informações de página.
            - z_surnames/z_collab: Informações do autor.
            - z_links/z_partial_body: Conteúdo adicional para desambiguação.
    """
    try:
        return xml_adapter.data
    except AttributeError:
        return dict(
            pkg_name=xml_adapter.sps_pkg_name,
            issn_print=xml_adapter.journal_issn_print,
            issn_electronic=xml_adapter.journal_issn_electronic,
            article_pub_year=xml_adapter.article_pub_year,
            pub_year=xml_adapter.pub_year,
            main_doi=xml_adapter.main_doi,
            elocation_id=xml_adapter.elocation_id,
            volume=xml_adapter.volume,
            number=xml_adapter.number,
            suppl=xml_adapter.suppl,
            fpage=xml_adapter.fpage,
            fpage_seq=xml_adapter.fpage_seq,
            lpage=xml_adapter.lpage,
            z_surnames=xml_adapter.z_surnames or None,
            z_collab=xml_adapter.z_collab or None,
            z_links=xml_adapter.z_links,
            z_partial_body=xml_adapter.z_partial_body,
        )
