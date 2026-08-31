from functools import cached_property

from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from core.utils.similarity import how_similar
from pid_provider import exceptions


def fix_get_data_to_compare(xml_adapter):
    """
    packtools 4.16.11
        {
            ...
            "z_partial_body": self.z_partial_body,
            ...
        }
    packtools > 4.17.0
        {
            ...
            "body_fragment_fingerprint": self.xml_with_pre.body_fragment_fingerprint,
            ...
        }
    """
    data = xml_adapter.get_data_to_compare()
    # independentemente da release do packtools,
    # o valor para z_partial_body na comparação é body_fragment_fingerprint
    data["body_fragment_fingerprint"] = xml_adapter.xml_with_pre.body_fragment_fingerprint
    return data


def fix_get_article_data(xml_with_pre, max_length=300):
    """
    Wrapper de compatibilidade em torno de xml_with_pre.get_article_data().

    Remove a chave legada "partial_body" do dict retornado (substituída
    por "body_fragment" nas versões atuais do packtools), evitando que
    código que consome esse dict dependa de uma chave que pode não
    refletir mais o valor realmente usado nas comparações de corpo do
    artigo.
    """
    try:
        data = xml_with_pre.readable_data
    except AttributeError:
        data = xml_with_pre.get_article_data(max_length)
        try:
            data.pop("partial_body")
        except KeyError:
            pass
    return data


def compare(registered_items, input_data):
    """
    Compara, item a item, os valores registrados (registered_items) com
    os valores do XML de entrada (input_data).

    Para cada label em registered_items, obtém o valor correspondente em
    input_data via `.get(label)` — um label ausente em input_data é
    tratado como None (não é pulado). Delega a comparação individual a
    compare_items() e agrega os scores.

    Returns
    -------
    dict
        {
            "items": lista de resultados de compare_items() (um por label),
            "total_score": soma dos scores individuais,
            "percentual_score": total_score / len(items),
        }

    Levanta ZeroDivisionError se registered_items estiver vazio (items
    fica vazio e a divisão por zero não é tratada explicitamente).
    """
    total_score = 0
    items = []
    for label, registered_item in registered_items.items():
        result = compare_items(label, registered_item, input_data.get(label))
        items.append(result)
        total_score += result["score"]
    return {
        "items": items,
        "total_score": total_score,
        "percentual_score": total_score / len(items)
    }


def compare_lists(registered, xml_adapter_titles):
    """
    Compara duas listas de textos (ex.: títulos de artigo) por
    similaridade de conjunto de palavras.

    Retorna 1 se as listas forem idênticas, 0 se qualquer uma das duas
    estiver vazia/None, ou o resultado de how_similar() entre as
    palavras únicas de cada lista (ordenadas e unidas em uma única
    string), caso contrário.
    """
    if xml_adapter_titles == registered:
        return 1
    if not xml_adapter_titles:
        return 0
    if not registered:
        return 0
    words1 = set()
    for item in xml_adapter_titles:
        words1.update(item.split())
    words2 = set()
    for item in registered:
        words2.update(item.split())
    return how_similar(" ".join(sorted(words1)), " ".join(sorted(words2)))


def compare_items(label, registered, input_data):
    """
    Compara um único item entre o valor registrado e o valor de entrada.

    - Se `registered` for uma lista (ex.: títulos), delega a
      compare_lists().
    - Caso os dois valores, normalizados (falsy vira None), sejam
      iguais, o score é 1.
    - Caso contrário, o score vem de how_similar() entre os dois valores
      (None é tratado como string vazia).

    Retorna um dict {"label": label, "score": score}, incluindo também
    "registered" quando o score não é 1 — útil para inspecionar
    divergências.
    """
    if isinstance(registered, list):
        score = compare_lists(registered, input_data)
    elif (input_data or None) == (registered or None):
        score = 1
    else:
        score = how_similar(input_data or "", registered or "")
    response = {"label": label, "score": score}
    if score != 1:
        response["registered"] = registered
        response["input_data"] = input_data
    return response


def get_score(registered, xml_data, min_value, max_value):
    """
    Score binário simples: max_value se registered == xml_data e ambos
    truthy; min_value se ambos forem iguais mas falsy (ex.: None ==
    None); 0 caso contrário.
    """
    if registered == xml_data:
        if registered:
            return max_value
        return min_value
    return 0


def zero_to_none(data):
    """
    Normaliza um campo numérico textual: retorna None se `data` for
    falsy; retorna `data` sem alteração se não for composto só de
    dígitos; e converte para None quando o valor numérico for zero
    (nos demais casos, mantém `data` como string, sem converter para
    int).
    """
    if not data:
        return
    if not data.isdigit():
        return data
    if int(data) == 0:
        return None
    return data


class QueryBuilderPidProviderXML:
    """
    Construtor de queries para busca de PidProviderXML.
    
    Centraliza toda a lógica de construção de queries complexas
    para buscar documentos por múltiplos critérios.
    """
    
    def __init__(self, xml_adapter):
        """
        Inicializa o construtor de queries obtendo os dados do adaptador.

        Parameters
        ----------
        xml_adapter : PidProviderXMLAdapter
            Adaptador com dados do XML para busca

        Define
        ------
        z_body_fragment : fingerprint sha256 de um fragmento estável do
            corpo do artigo (XMLWithPre.body_fragment_fingerprint),
            acessado direto do xml_with_pre — não requer nenhuma
            mudança no packtools nem no PidProviderXMLAdapter. É mais
            robusto que z_partial_body (que é só o primeiro parágrafo
            não vazio e pode colidir entre artigos diferentes, ex.:
            rótulos de seção genéricos como "ARTIGO DE REVISÃO").
        z_partial_body : hash legado do corpo do artigo
            (xml_with_pre.z_partial_body), mantido apenas para casar
            com registros antigos.
        adapter_data : dict bruto de xml_adapter.data.
        xml_with_pre_data : dict normalizado retornado por
            fix_get_article_data(xml_adapter.xml_with_pre, 300) — já
            sem a chave legada "partial_body".
        """
        self.xml_adapter = xml_adapter
        self.z_body_fragment = xml_adapter.xml_with_pre.body_fragment_fingerprint
        self.z_partial_body = xml_adapter.z_partial_body
        self.adapter_data = xml_adapter.data
        self.xml_with_pre_data = fix_get_article_data(xml_adapter.xml_with_pre, 300)

    @property
    def pkg_name_list(self):
        """
        Consolida, em um único set, todos os nomes de pacote possíveis
        para o artigo: o nome enviado via parâmetro no construtor, o
        nome oficial atual calculado pelo packtools (sps_pkg_name) e
        todos os nomes depreciados/alternativos já usados no passado.
        Valores falsy são descartados.
        """
        pkg_names = set()
        if self.xml_adapter.pkg_name:
            pkg_names.add(self.xml_adapter.pkg_name)
        if self.xml_adapter.sps_pkg_name:
            pkg_names.add(self.xml_adapter.sps_pkg_name)
        pkg_names.update(self.xml_adapter.xml_with_pre.deprecated_sps_pkg_name_list)
        return set(item for item in pkg_names if item)
    
    def validate_input_data(self):
        """
        Garante que o XML de entrada tem parâmetros suficientes para
        localizar um registro existente.

        Levanta:
        - RequiredPublicationYearErrorToGetPidProviderXMLError se não
          houver ano de publicação;
        - RequiredISSNErrorToGetPidProviderXMLError se não houver ISSN
          eletrônico nem impresso;
        - NotEnoughParametersToGetPidProviderXMLError se, além do
          ano/ISSN, não houver nenhum dado de localização do artigo
          (elocation_id/fpage/lpage/etc.) nem nenhum dado textual
          (títulos, sobrenomes, colaboradores, links ou fragmento do
          corpo) que permita diferenciar o artigo de outros do mesmo
          fascículo.
        """
        if not self.adapter_data.get("pub_year"):
            raise exceptions.RequiredPublicationYearErrorToGetPidProviderXMLError()
        issn_electronic = self.adapter_data.get("issn_electronic")
        issn_print = self.adapter_data.get("issn_print")
        if not issn_electronic and not issn_print:
            raise exceptions.RequiredISSNErrorToGetPidProviderXMLError()
        items = list(self.article_location_params.values())
        if any(items):
            return
        article_titles = (self.xml_with_pre_data.get("article_titles") or [])
        article_titles = [x for x in article_titles if x]
        items = [
            article_titles,
            self.xml_with_pre_data.get("surnames"),
            self.xml_with_pre_data.get("collab"),
            self.xml_with_pre_data.get("links"),
            self.xml_with_pre_data.get("body_fragment"),
        ]
        if any(items):
            return
        raise exceptions.NotEnoughParametersToGetPidProviderXMLError()

    # ========== Queries Construídas ==========
    
    @property
    def identifier_queries(self):
        """
        Constrói queries para busca por identificadores (v3, v2, aop_pid, pkg_name, DOI).
        """
        q = Q()
        
        v3 = self.xml_adapter.v3
        v2 = self.xml_adapter.v2
        aop_pid = self.xml_adapter.aop_pid
    
        if v3:
            q |= Q(v3=v3)
        
        if v2:
            q |= Q(v2=v2)
        
        if aop_pid:
            q |= Q(v2=aop_pid) | Q(aop_pid=aop_pid)
            
        pkg_names = self.pkg_name_list
        if pkg_names:
            q |= Q(pkg_name__in=pkg_names)

        main_doi = self.adapter_data.get("main_doi")
        if main_doi:
            q |= Q(main_doi=main_doi)
            
        return q
    
    @property
    def issn_query(self):
        """
        Constrói query base para busca por ISSN (eletrônico ou impresso).
        """
        q = Q()
        issn_electronic = self.adapter_data.get("issn_electronic")
        issn_print = self.adapter_data.get("issn_print")
        
        if not issn_electronic and not issn_print:
            raise exceptions.RequiredISSNErrorToGetPidProviderXMLError(
                _("Required Print or Electronic ISSN to identify XML {}").format(
                    self.xml_adapter.pkg_name,
                )
            )
        
        if issn_electronic:
            q |= Q(issn_electronic=issn_electronic)
        
        if issn_print:
            q |= Q(issn_print=issn_print)
        
        return q
           
    @property
    def issue_params(self):
        """
        Constrói dicionário com metadados do fascículo e paginação do artigo.
        """
        return {
            "pub_year": self.adapter_data.get("pub_year"),
            "volume": self.adapter_data.get("volume"),
            "number": self.adapter_data.get("number"),
            "suppl": self.adapter_data.get("suppl"),
        }

    @property
    def article_location_params(self):
        """
        Constrói dicionário com metadados de localização do artigo.
        """
        data = {
            "elocation_id": self.adapter_data.get("elocation_id"),
            "fpage": self.adapter_data.get("fpage"),
            "fpage_seq": self.adapter_data.get("fpage_seq"),
            "lpage": self.adapter_data.get("lpage"),
        }
        order = self.xml_adapter.order
        if order:
            data["v2__endswith"] = order
        return data

    @property
    def partial_body_query(self):
        """
        Constrói a query para o campo z_partial_body, que hoje armazena
        dois formatos possíveis de hash, dependendo de quando o registro
        foi salvo:

        - legado: self.z_partial_body
          (xml_adapter.xml_with_pre.z_partial_body) — hash do primeiro
          parágrafo não vazio do corpo;
        - atual: self.z_body_fragment
          (xml_with_pre.body_fragment_fingerprint), gravado no mesmo
          campo z_partial_body a partir desta correção (sem necessidade
          de migração/backfill).

        Usa IN com os hashes disponíveis do XML de entrada para casar
        com candidatos em qualquer um dos dois formatos.

        Quando o XML de entrada não tem NENHUM dos dois hashes
        calculados (ambos None), não é seguro usar
        `z_partial_body__in=(None, None)`: em SQL, `IN` é uma cadeia de
        igualdades e `NULL = NULL` é UNKNOWN (nunca True), então essa
        forma jamais encontraria candidatos com z_partial_body nulo.
        Nesse caso, usamos `z_partial_body__isnull=True` explicitamente,
        preservando o comportamento equivalente ao antigo
        `Q(z_partial_body=None)` (que o Django traduz para IS NULL).
        """
        candidates = set(v for v in (self.z_partial_body, self.z_body_fragment) if v)
        if candidates:
            return Q(z_partial_body__in=candidates)
        return Q(z_partial_body__isnull=True)

    @property
    def article_data_query(self):
        """
        Constrói query para busca por dados textuais codificados (hashes
        sha256 de sobrenomes, colaboradores e links), combinada com
        partial_body_query (hash/fingerprint do corpo do artigo).
        """
        z_surnames = self.adapter_data.get("z_surnames")
        z_collab = self.adapter_data.get("z_collab")
        z_links = self.adapter_data.get("z_links")

        return Q(
            z_surnames=z_surnames,
            z_collab=z_collab,
            z_links=z_links,
        ) & self.partial_body_query

    def get_article_data_query(self, issue):
        """
        Combina article_data_query com os parâmetros de fascículo e
        localização do artigo (quando `issue` é truthy), ou exige que
        todos os campos de localização estejam nulos (quando `issue` é
        falsy) — caso de artigos sem paginação/localização definida
        (ex.: ahead-of-print).
        """
        if issue:
            return (
                self.article_data_query & 
                Q(**self.issue_params) & 
                Q(**self.article_location_params)
            )
        return (
            self.article_data_query & 
            Q(
                volume__isnull=True,
                number__isnull=True,
                suppl__isnull=True,
                elocation_id__isnull=True,
                fpage__isnull=True,
                lpage__isnull=True,
            )
        )
