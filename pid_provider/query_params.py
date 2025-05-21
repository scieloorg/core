from django.db.models import Q

from pid_provider import exceptions


def get_valid_query_parameters(xml_adapter):
    """
    Obtém parâmetros válidos para consulta com base em um adaptador XML.
    
    Esta função determina os parâmetros de consulta válidos para localizar documentos
    relacionados a um artigo científico, usando diferentes estratégias dependendo 
    se o artigo é um 'ahead of print' (AOP) ou um artigo regular.
    
    Args:
        xml_adapter: Um objeto adaptador XML contendo metadados do artigo.
    
    Returns:
        tuple: Uma tupla contendo (expressão_q, lista_de_parâmetros_válidos)
              onde expressão_q é um objeto Q para filtrar por ISSN e
              lista_de_parâmetros_válidos é uma lista de dicionários com parâmetros válidos.
    
    Raises:
        RequiredPublicationYearErrorToGetPidProviderXMLError: Se o ano de publicação requerido não estiver disponível.
        RequiredISSNErrorToGetPidProviderXMLError: Se nem o ISSN eletrônico nem o impresso estiverem disponíveis.
        NotEnoughParametersToGetPidProviderXMLError: Se os parâmetros disponíveis forem insuficientes para desambiguação.
    """
    q = None
    try:
        q = get_journal_q_expression(xml_adapter)
    except exceptions.RequiredISSNErrorToGetPidProviderXMLError:
        raise

    basic_params = get_basic_params(xml_adapter)
    if xml_adapter.is_aop:
        kwargs = [
            _get_valid_params(xml_adapter, basic_params)
        ]
    else:
        kwargs = [
            _get_valid_params(
                add_issue_params(xml_adapter, basic_params, filter_by_issue=True)),
            _get_valid_params(
                add_issue_params(xml_adapter, basic_params, aop_version=True)),
        ]
    return q, kwargs


def add_issue_params(xml_adapter, basic_params, filter_by_issue=None, aop_version=None):
    """
    Adiciona parâmetros relacionados à edição aos parâmetros básicos.
    
    Args:
        xml_adapter: Um objeto adaptador XML contendo metadados do artigo.
        basic_params (dict): Dicionário com parâmetros básicos.
        filter_by_issue (bool, optional): Se True, filtra por edição específica. Padrão é None.
        aop_version (bool, optional): Se True, configura parâmetros para versão "ahead of print". Padrão é None.
    
    Returns:
        dict: Dicionário combinado de parâmetros básicos e parâmetros da edição.
    """
    params = get_issue_params(xml_adapter, filter_by_issue, aop_version)
    params.update(basic_params)
    return params


def _get_valid_params(xml_adapter, params):
    """
    Valida e complementa os parâmetros fornecidos com parâmetros de desambiguação, se necessário.
    
    Esta função interna tenta validar os parâmetros fornecidos e, se houver falta de 
    informações sobre autores, tenta adicionar parâmetros de desambiguação.
    
    Args:
        xml_adapter: Um objeto adaptador XML contendo metadados do artigo.
        params (dict): Dicionário com parâmetros a serem validados.
    
    Returns:
        dict: Dicionário de parâmetros validados e complementados, se necessário.
    
    Raises:
        NotEnoughParametersToGetPidProviderXMLError: Se não houver parâmetros suficientes para desambiguação.
        RequiredPublicationYearErrorToGetPidProviderXMLError: Se o ano de publicação requerido não estiver disponível.
    """
    valid_params = {}
    valid_params.update(params)
    try:
        validate_query_params(valid_params)
    except exceptions.RequiredAuthorErrorToGetPidProviderXMLError:
        try:
            disambiguation_params = get_disambiguation_params(xml_adapter)
            valid_params.update(disambiguation_params)
        except exceptions.NotEnoughParametersToGetPidProviderXMLError:
            raise
    except exceptions.RequiredPublicationYearErrorToGetPidProviderXMLError:
        raise
    return valid_params


def get_journal_q_expression(xml_adapter):
    """
    Cria uma expressão Q para filtrar por ISSN eletrônico ou impresso.
    
    Args:
        xml_adapter: Um objeto adaptador XML contendo metadados do artigo.
    
    Returns:
        Q: Um objeto Q para filtrar por ISSN eletrônico ou impresso.
    
    Raises:
        RequiredISSNErrorToGetPidProviderXMLError: Se nem o ISSN eletrônico nem o impresso estiverem disponíveis.
    """
    q = Q()
    if xml_adapter.issn_electronic:
        q |= Q(issn_electronic=xml_adapter.issn_electronic)
    if xml_adapter.journal_issn_print:
        q |= Q(issn_print=xml_adapter.journal_issn_print)
    if not xml_adapter.issn_electronic and not xml_adapter.journal_issn_print:
        raise exceptions.RequiredISSNErrorToGetPidProviderXMLError(
            _("Required Print or Electronic ISSN to identify XML {}").format(
                xml_adapter.pkg_name,
            )
        )
    return q


def get_basic_params(xml_adapter):
    """
    Obtém parâmetros básicos do artigo a partir do adaptador XML.
    
    Extrai informações como sobrenomes de autores, colaboradores, DOI, 
    ID de localização eletrônica e ano de publicação do artigo.
    
    Args:
        xml_adapter: Um objeto adaptador XML contendo metadados do artigo.
    
    Returns:
        dict: Dicionário contendo parâmetros básicos do artigo.
    """
    _params = dict(
        z_surnames=xml_adapter.z_surnames or None,
        z_collab=xml_adapter.z_collab or None,
    )
    if xml_adapter.main_doi:
        _params["main_doi__iexact"] = xml_adapter.main_doi
    _params["elocation_id__iexact"] = xml_adapter.elocation_id
    _params["article_pub_year"] = xml_adapter.article_pub_year
    return _params


def get_issue_params(xml_adapter, filter_by_issue=False, aop_version=False):
    """
    Obtém parâmetros relacionados à edição a partir do adaptador XML.
    
    Dependendo dos flags, configura parâmetros para filtrar por edição específica 
    ou para configurar uma consulta para versão "ahead of print".
    
    Args:
        xml_adapter: Um objeto adaptador XML contendo metadados do artigo.
        filter_by_issue (bool, optional): Se True, incluir parâmetros para filtrar 
                                         por edição específica. Padrão é False.
        aop_version (bool, optional): Se True, configurar parâmetros para versão 
                                     "ahead of print". Padrão é False.
    
    Returns:
        dict: Dicionário contendo parâmetros relacionados à edição.
    """
    _params = {}
    if aop_version:
        _params["volume__isnull"] = True
        _params["number__isnull"] = True
        _params["suppl__isnull"] = True
    elif filter_by_issue:
        _params["pub_year"] = xml_adapter.pub_year
        _params["volume__iexact"] = xml_adapter.volume
        _params["number__iexact"] = xml_adapter.number
        _params["suppl__iexact"] = xml_adapter.suppl
        _params["fpage__iexact"] = xml_adapter.fpage
        _params["fpage_seq__iexact"] = xml_adapter.fpage_seq
        _params["lpage__iexact"] = xml_adapter.lpage
    return _params


def get_disambiguation_params(xml_adapter):
    """
    Obtém parâmetros adicionais para desambiguação.
    
    Quando os parâmetros básicos não são suficientes para identificar 
    unicamente um artigo, essa função fornece parâmetros adicionais para desambiguação.
    
    Args:
        xml_adapter: Um objeto adaptador XML contendo metadados do artigo.
    
    Returns:
        dict: Dicionário contendo parâmetros de desambiguação.
    
    Raises:
        NotEnoughParametersToGetPidProviderXMLError: Se não houver parâmetros 
                                                    suficientes para desambiguação.
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
    Valida se os parâmetros de consulta contêm informações suficientes.
    
    Verifica se os parâmetros de consulta contêm ano de publicação e 
    pelo menos um identificador único (DOI, página inicial ou ID de localização eletrônica) 
    ou informações de autor.
    
    Args:
        query_params (dict): Dicionário contendo parâmetros de consulta.
    
    Returns:
        bool: True se os parâmetros forem válidos.
    
    Raises:
        RequiredPublicationYearErrorToGetPidProviderXMLError: Se o ano de publicação não estiver disponível.
        RequiredAuthorErrorToGetPidProviderXMLError: Se não houver informações de autor e 
                                                   nenhum identificador único disponível.
    """
    _params = query_params
    if not any(
        [
            _params.get("article_pub_year"),
            _params.get("pub_year"),
        ]
    ):
        raise exceptions.RequiredPublicationYearErrorToGetPidProviderXMLError(
            _("Required issue or article publication year {}").format(
                _params,
            )
        )

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
    Extrai todos os dados relevantes de um adaptador XML em um dicionário.
    
    Esta função tenta acessar o atributo 'data' do adaptador XML e, se não estiver 
    disponível, cria um dicionário com todos os atributos relevantes manualmente.
    
    Args:
        xml_adapter: Um objeto adaptador XML contendo metadados do artigo.
    
    Returns:
        dict: Dicionário contendo todos os metadados do artigo extraídos do adaptador XML.
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
            z_journal_title=xml_adapter.z_journal_title,
            z_article_titles_texts=xml_adapter.z_article_titles_texts,
        )