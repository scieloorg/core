from functools import cached_property

from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from core.utils.similarity import how_similar
from pid_provider import exceptions


def compare(registered_items, input_data):
    """
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
    if isinstance(registered, list):
        score = compare_lists(registered, input_data)
    elif (input_data or None) == (registered or None):
        score = 1
    else:
        score = how_similar(input_data or "", registered or "")
    response = {"label": label, "score": score}
    if score != 1:
        response["registered"] = registered
    return response


def get_score(registered, xml_data, min_value, max_value):
    if registered == xml_data:
        if registered:
            return max_value
        return min_value
    return 0


def zero_to_none(data):
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
        Inicializa o construtor de queries obtendo os dicionários de dados do adaptador.
        
        Parameters
        ----------
        xml_adapter : PidProviderXMLAdapter
            Adaptador com dados do XML para busca
        """
        self.xml_adapter = xml_adapter
        # Centraliza o acesso aos dados brutos e normalizados (hashes de 64 chars)
        # z_body_fragment: fingerprint sha256 do corpo INTEIRO do artigo
        # (XMLWithPre.body_fragment_fingerprint), acessado direto do
        # xml_with_pre — não requer nenhuma mudança no packtools nem no
        # PidProviderXMLAdapter. É mais robusto que z_partial_body (que
        # é só o primeiro parágrafo não vazio e pode colidir entre
        # artigos diferentes, ex.: rótulos de seção genéricos como
        # "ARTIGO DE REVISÃO").
        self.z_body_fragment = xml_adapter.xml_with_pre.body_fragment_fingerprint
        self.adapter_data = xml_adapter.data
        self.compare_data = xml_adapter.get_data_to_compare()
        self.xml_with_pre_data = xml_adapter.xml_with_pre.get_article_data(300)

    @property
    def pkg_name_list(self):
        # --- Resolução Consolidada de Package Names ---
        pkg_names = set()
        # 1. Nome enviado originalmente via parâmetro no construtor
        if self.xml_adapter.pkg_name:
            pkg_names.add(self.xml_adapter.pkg_name)
        # 2. Nome oficial atual gerado pelo motor de cálculo do XML
        if self.xml_adapter.sps_pkg_name:
            pkg_names.add(self.xml_adapter.sps_pkg_name)
        # 3. Consolida todas as listas de nomes depreciados/alternativos
        pkg_names.update(self.xml_adapter.xml_with_pre.deprecated_sps_pkg_name_list)
        return set(item for item in pkg_names if item)
    
    def validate_input_data(self):
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
            self.xml_with_pre_data.get("partial_body"),
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
        other_pids = set()
        
        # PIDs diretos do xml_adapter (não envelopados no data dict)
        v3 = self.xml_adapter.v3
        v2 = self.xml_adapter.v2
        aop_pid = self.xml_adapter.aop_pid
    
        # PID v3 - máxima prioridade
        if v3:
            q |= Q(v3=v3)
        
        # PID v2
        if v2:
            q |= Q(v2=v2)
        
        # AOP PID
        if aop_pid:
            q |= Q(v2=aop_pid) | Q(aop_pid=aop_pid)
            
        # Package names históricos e atuais
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

        - legado: hash de z_partial_body (primeiro parágrafo não vazio
          do corpo, via xml_adapter.z_partial_body);
        - atual: fingerprint do corpo INTEIRO do artigo
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
        z_partial_body = self.adapter_data.get("z_partial_body")
        candidates = set(v for v in (z_partial_body, self.z_body_fragment) if v)
        if candidates:
            return Q(z_partial_body__in=candidates)
        return Q(z_partial_body__isnull=True)

    @property
    def article_data_query(self):
        """
        Constrói query para busca por dados textuais codificados (hashes sha256).
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