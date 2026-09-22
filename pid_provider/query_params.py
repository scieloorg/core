from django.conf import settings
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from core.utils.similarity import how_similar
from pid_provider import exceptions


def fix_xml_with_pre_data(xml_with_pre):
    data = xml_with_pre.data
    try:
        pkg_names = xml_with_pre.pkg_name_variations
    except AttributeError:
        return data

    data["pkg_names"] = sorted(item for item in (pkg_names or []) if item)
    return data


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
    xml_with_pre = xml_adapter.xml_with_pre
    data["body_fragment_fingerprint"] = xml_with_pre.body_fragment_fingerprint
    data["surnames"] = xml_with_pre.surnames
    data["pid_v2"] = xml_with_pre.v2
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
    Compara os metadados do registro gravado (registered_items) com os dados
    do XML de entrada (input_data).

    O loop é ditado exclusivamente pelas chaves presentes em registered_items.
    Campos em que ambos os lados são falsy/None são descartados do divisor.
    """
    total_score = 0.0
    total_items = 0
    items = []

    for label, registered_item in registered_items.items():
        input_data_item = input_data.get(label)

        # Se o banco e a entrada forem nulos/falsy para este campo, não conta na média
        if registered_item is None and input_data_item is None:
            items.append({"label": label, "score": 1.0, "ignored": True})
            continue

        result = compare_items(label, registered_item, input_data_item)
        items.append(result)

        total_score += result["score"]
        total_items += 1

    percentual_score = (total_score / total_items) if total_items > 0 else 0.0

    return {
        "items": items,
        "total_score": total_score,
        "percentual_score": percentual_score,
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
    elif input_data == registered:
        score = 1
    elif label.startswith("z_") or 'finger' in label:
        score = 0
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
        try:
            pkg_names = self.xml_adapter.xml_with_pre.pkg_name_variations
        except AttributeError:
            pass
        else:
            return {item for item in (pkg_names or []) if item}

        pkg_names = set()
        if self.xml_adapter.pkg_name:
            pkg_names.add(self.xml_adapter.pkg_name)
        if self.xml_adapter.sps_pkg_name:
            pkg_names.add(self.xml_adapter.sps_pkg_name)
        pkg_names.update(self.xml_adapter.xml_with_pre.deprecated_sps_pkg_name_list)
        return {item for item in pkg_names if item}
    
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
        Constrói query para busca por identificadores diretos (v3, v2,
        aop_pid, DOI principal).

        Separada de pkg_name_queries (ver docstring de pkg_name_queries
        para o porquê) para que cada uma seja executada como uma etapa
        própria em select_records, do critério mais específico
        (identificadores) para o mais genérico (nome de pacote).

        Quando nenhum dos identificadores está presente, retorna Q()
        (query vazia). Q() não deve ser usada diretamente em
        queryset.filter(): em Django, filter(Q()) não restringe nada e
        retornaria TODOS os registros, o que aqui significaria "nenhum
        critério" e não "qualquer registro serve". Por isso o consumidor
        (PidProviderXML.select_records) trata explicitamente o caso
        `identifier_queries == Q()` como "sem candidatos" antes de
        filtrar.
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

        main_doi = self.adapter_data.get("main_doi")
        if main_doi:
            q |= Q(main_doi=main_doi)

        return q

    @property
    def pkg_name_queries(self):
        """
        Constrói query para busca por nome(s) de pacote (pkg_name_list).

        Extraída de identifier_queries para ser executada como etapa
        própria em select_records, logo em seguida à busca por
        identificadores diretos (v3/v2/aop_pid/DOI) — pkg_name é menos
        específico que esses (pode colidir entre revisões/depósitos do
        mesmo artigo), por isso roda depois, não junto.

        Mesma observação de identifier_queries sobre Q(): quando não há
        nenhum pkg_name disponível, retorna Q() e o consumidor deve
        tratar esse caso como "sem candidatos", não filtrar com ele.
        """
        pkg_names = self.pkg_name_list
        if pkg_names:
            return Q(pkg_name__in=pkg_names)
        return Q()

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

    def get_article_data_query(self, issue, flexible):
        """
        Constrói uma variante da query de candidatos por dados do
        artigo, combinando dois eixos independentes: `issue` (o
        candidato TEM ou NÃO TEM fascículo/localização) e `flexible`
        (a busca EXIGE ou NÃO os hashes textuais do artigo). As 4
        combinações resultantes são usadas por select_records como
        alternativas (OR) — da mais estrita à mais permissiva — para
        achar candidatos mesmo quando o conteúdo textual do artigo foi
        corrigido (errata) mas fascículo/localização permanecem iguais.

        Parameters
        ----------
        issue : bool
            Truthy: exige que o candidato case com `issue_params`
            (pub_year/volume/number/suppl) E `article_location_params`
            (elocation_id/fpage/fpage_seq/lpage/v2__endswith) — caso
            normal, com fascículo e paginação definidos.
            Falsy: exige o oposto — todos os campos de
            volume/number/suppl/elocation_id/fpage/lpage NULOS no
            candidato — caso de artigos sem paginação/localização
            definida (ex.: ahead-of-print).
        flexible : bool
            False (estrito): exige TAMBÉM que `article_data_query`
            (hashes de sobrenomes/colaboradores/links + fingerprint do
            corpo) do candidato case com os do XML de entrada. É a
            busca original, sem afrouxamento.
            True: DISPENSA essa exigência de conteúdo textual — casa só
            por fascículo/localização (quando `issue`) ou só pela
            ausência delas combinada com `article_location_params`
            (quando não `issue`). Serve para achar o mesmo artigo
            depois que seu conteúdo textual mudou.
        """
        if issue:
            q = (
                Q(**self.issue_params) & 
                Q(**self.article_location_params)
            )
            if flexible:
                return q
            return self.article_data_query & q
        # not issue
        q = Q(
            volume__isnull=True,
            number__isnull=True,
            suppl__isnull=True,
            elocation_id__isnull=True,
            fpage__isnull=True,
            lpage__isnull=True,
        )
        if flexible:
            return q & Q(**self.article_location_params)
        return q & self.article_data_query

def get_best_match(results, xml_adapter_data):
    """
    Compara uma lista de candidatos (PidProviderXML) com os dados do XML
    recebido e classifica os candidatos por similaridade.

    Parameters
    ----------
    results : list[PidProviderXML]
        Lista JÁ MATERIALIZADA (não queryset) de candidatos a comparar.
    xml_adapter_data : dict
        Dados de comparação do XML de entrada, ou seja, o retorno de
        ``xml_adapter.get_data_to_compare()``.

    Returns
    -------
    dict
        Todas as chaves abaixo são OPCIONAIS — só aparecem quando há
        conteúdo para elas. Use ``.get(...)`` ou ``"chave" in result``
        ao consumir o retorno, nunca acesso direto.

        - ``"unmatched"``: presente apenas se houver ao menos 1
        candidato com ``percentual_score`` <= min_rate. Lista de
        ``item.data`` desses candidatos.
        - ``"registered"``: presente apenas se houver ao menos 1
        candidato aprovado (score > min_rate). Contém o OBJETO
        ``PidProviderXML`` (não o dict ``.data``) do candidato com
        maior score — em caso de empate, o critério de desempate é
        ``updated`` mais recente e, em seguida, maior ``id``.
        - ``"matched"``: presente apenas se houver 2 OU MAIS candidatos
        aprovados, EXCLUINDO os empatados em 1º lugar com "registered"
        (ver "multiple_matched"). Contém ``item.data`` dos candidatos
        aprovados com score estritamente menor que o máximo, na mesma
        ordem de score decrescente.
        - ``"multiple_matched"``: presente apenas se houver 2 OU MAIS
        candidatos aprovados. Contém ``item.data`` dos candidatos
        empatados em score com "registered" (score == score máximo),
        excluindo o próprio "registered".
    """
    detail = {}
    found = []
    items = {}
    responses = {}
    min_rate = settings.PID_PROVIDER_MIN_RATE
    for item in results:
        item_data = item.data_to_compare
        response = compare(item_data, xml_adapter_data)
        items[item.id] = item
        responses[item.id] = response
        found.append((response["percentual_score"], item.updated.isoformat(), item.id))
    found = sorted(found, reverse=True)

    matched = []
    unmatched = []
    for percentual_score, updated, item_id in found:
        data = {"data": items[item_id].data, "response": responses[item_id]}
        if percentual_score > min_rate:
            matched.append(data)
        else:
            unmatched.append(data)
    if matched:
        registered_id = found[0][-1]
        detail["registered"] = items[registered_id]
        max_percentual_score = responses[registered_id]["percentual_score"]
        if len(matched) > 1:
            detail["matched"] = []
            detail["multiple_matched"] = []
            for matched_item in matched[1:]:
                if matched_item["response"]["percentual_score"] == max_percentual_score:
                    detail["multiple_matched"].append(matched_item)
                else:
                    detail["matched"].append(matched_item)
            if detail["multiple_matched"]:
                detail["multiple_matched"].insert(0, matched[0])
    if unmatched:
        detail["unmatched"] = unmatched
    return detail


def select_record(xml_adapter, selection_results):
    """
    Consome os pares (label, lista_de_candidatos) produzidos por
    PidProviderXML.select_records. As listas já vêm materializadas,
    então aqui só checamos truthiness (nunca .exists()/.count() sobre
    queryset).

    `multiple_matched_items` (quando presente) contém candidatos empatados
    em score com "registered" (ver get_best_match) -- ou seja, escolher
    "registered" entre eles foi arbitrário (desempate por `updated`/`id`).
    O consumidor (PidProviderXML.register/.is_registered) trata essa chave
    como ambiguidade e levanta UnmatchedPidProviderXMLError antes de
    aceitar "registered".
    """
    unmatched_items = {}
    xml_adapter_data_to_compare = fix_get_data_to_compare(xml_adapter)
    for label, results in selection_results:
        if not results:
            continue

        result = get_best_match(results, xml_adapter_data_to_compare)

        matched = result.get("matched")
        multiple_matched = result.get("multiple_matched")
        unmatched = result.get("unmatched")
        registered = result.get("registered")
        if registered:
            response = {
                "total_results": len(results),
                "registered": registered,
            }
            if matched:
                response["matched_items"] = {label: matched}
            if multiple_matched:
                response["multiple_matched_items"] = {label: multiple_matched}
            if unmatched:
                response["unmatched_items"] = {label: unmatched}
            return response

        if unmatched:
            unmatched_items[label] = unmatched

    if unmatched_items:
        return {"unmatched_items": unmatched_items}
    return {}
