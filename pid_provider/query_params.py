from functools import cached_property

from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from core.utils.profiling_tools import profile_function
from pid_provider import exceptions


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
        Inicializa o construtor de queries.
        
        Parameters
        ----------
        xml_adapter : PidProviderXMLAdapter
            Adaptador com dados do XML para busca
        """
        self.xml_adapter = xml_adapter
    
    # ========== Cached Properties para Atributos do XML Adapter ==========
    
    @cached_property
    def v3(self):
        """PID v3 do documento."""
        return self.xml_adapter.v3
    
    @cached_property
    def v2(self):
        """PID v2 do documento."""
        return self.xml_adapter.v2
    
    @cached_property
    def aop_pid(self):
        """PID AOP (Ahead of Print) do documento."""
        return self.xml_adapter.aop_pid
    
    @cached_property
    def pkg_name(self):
        """Nome do pacote do documento."""
        return self.xml_adapter.pkg_name
    
    @cached_property
    def main_doi(self):
        """DOI principal do documento."""
        return self.xml_adapter.main_doi
    
    @cached_property
    def journal_issn_electronic(self):
        """ISSN eletrônico do periódico."""
        return self.xml_adapter.journal_issn_electronic
    
    @cached_property
    def journal_issn_print(self):
        """ISSN impresso do periódico."""
        return self.xml_adapter.journal_issn_print
    
    @cached_property
    def elocation_id(self):
        """Identificador de localização eletrônica."""
        return self.xml_adapter.elocation_id
    
    @cached_property
    def fpage(self):
        """Primeira página do artigo."""
        return self.xml_adapter.fpage
    
    @cached_property
    def fpage_seq(self):
        """Sequência da primeira página."""
        return self.xml_adapter.fpage_seq
    
    @cached_property
    def lpage(self):
        """Última página do artigo."""
        return self.xml_adapter.lpage
    
    @cached_property
    def pub_year(self):
        """Ano de publicação."""
        return self.xml_adapter.pub_year
    
    @cached_property
    def volume(self):
        """Volume da publicação."""
        return self.xml_adapter.volume
    
    @cached_property
    def number(self):
        """Número/fascículo da publicação."""
        return self.xml_adapter.number
    
    @cached_property
    def suppl(self):
        """Suplemento da publicação."""
        return self.xml_adapter.suppl
    
    @cached_property
    def z_surnames(self):
        """Sobrenomes dos autores concatenados."""
        return self.xml_adapter.z_surnames
    
    @cached_property
    def z_collab(self):
        """Colaborações do artigo."""
        return self.xml_adapter.z_collab
    
    @cached_property
    def z_links(self):
        """Links relacionados ao artigo."""
        return self.xml_adapter.z_links
    
    @cached_property
    def z_partial_body(self):
        """Conteúdo parcial do corpo do artigo."""
        return self.xml_adapter.z_partial_body

    @cached_property
    def order(self):
        """Conteúdo parcial do corpo do artigo."""
        return self.xml_adapter.order
    
    # ========== Queries Construídas ==========
    
    @cached_property
    def identifier_queries(self):
        """
        Constrói queries para busca por identificadores (v3, v2, aop_pid, pkg_name, DOI).
        
        Busca em múltiplos campos incluindo other_pid para garantir
        compatibilidade com diferentes formatos de PIDs.
        
        Returns
        -------
        Q
            Query object combinando buscas por v3, v2, aop_pid, pkg_name e main_doi
        """
        q = Q()
        
        # PID v3 - máxima prioridade
        if self.v3:
            q |= Q(v3=self.v3)
        
        # PID v2
        if self.v2:
            q |= Q(v2=self.v2)
        
        # AOP PID
        if self.aop_pid:
            q |= Q(v2=self.aop_pid) | Q(aop_pid=self.aop_pid)
            
        # Package name
        if self.pkg_name:
            q |= Q(pkg_name=self.pkg_name)

        # # DOI principal
        # if self.main_doi:
        #     q |= Q(main_doi=self.main_doi)

        return q
    
    @cached_property
    def issn_query(self):
        """
        Constrói query base para busca por ISSN (eletrônico ou impresso).
        
        Returns
        -------
        Q
            Query object combinando ISSN eletrônico e impresso com operador OR
        
        Raises
        ------
        RequiredISSNErrorToGetPidProviderXMLError
            Se nenhum ISSN (eletrônico ou impresso) estiver disponível
        """
        q = Q()
        
        if not self.journal_issn_electronic and not self.journal_issn_print:
            raise exceptions.RequiredISSNErrorToGetPidProviderXMLError(
                _("Required Print or Electronic ISSN to identify XML {}").format(
                    self.pkg_name,
                )
            )
        
        if self.journal_issn_electronic:
            q |= Q(issn_electronic=self.journal_issn_electronic)
        
        if self.journal_issn_print:
            q |= Q(issn_print=self.journal_issn_print)
        
        return q
           
    @cached_property
    def issue_params(self):
        """
        Constrói dicionário com metadados do fascículo e paginação do artigo.
        
        Retorna todos os campos sem verificar presença, permitindo
        que o ORM do Django filtre automaticamente valores None.
        
        Returns
        -------
        dict
            Dicionário com elocation_id, fpage, fpage_seq, lpage, 
            pub_year, volume, number e suppl
        """
        data = {
            "elocation_id": self.elocation_id,
            "fpage": self.fpage,
            "fpage_seq": self.fpage_seq,
            "lpage": self.lpage,
            "pub_year": self.pub_year,
            "volume": self.volume,
            "number": self.number,
            "suppl": self.suppl,
        }
        if self.order:
            data["v2__endswith"] = self.order
        elif not self.elocation_id and not self.fpage and self.main_doi:
            data["main_doi__iexact"] = self.main_doi
        return data
    
    @cached_property
    def article_data_query(self):
        """
        Constrói query para busca por dados textuais do artigo.
        
        Combina buscas por sobrenomes de autores, colaborações,
        links e conteúdo parcial do corpo do artigo.
        
        Returns
        -------
        Q or None
            Query object combinando z_surnames, z_collab, z_links e z_partial_body,
            ou None se nenhum dado textual estiver disponível
        """
        # Verifica se há algum dado textual disponível
        if not any([
            self.z_surnames,
            self.z_collab,
            self.z_links,
            self.z_partial_body,
        ]):
            return Q(
                z_surnames=self.z_surnames,
                z_collab=self.z_collab,
                z_links=self.z_links,
                z_partial_body=self.z_partial_body,
            )
        
        q = Q()
        
        # Adiciona query para sobrenomes se disponível
        if self.z_surnames:
            q |= Q(z_surnames=self.z_surnames)
        
        # Adiciona queries para outros campos textuais
        if self.z_collab:
            q |= Q(z_collab=self.z_collab)
        
        if self.z_links:
            q |= Q(z_links=self.z_links)
        
        if self.z_partial_body:
            q |= Q(z_partial_body=self.z_partial_body)
        
        return q