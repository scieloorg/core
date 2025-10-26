from functools import cached_property

from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from core.utils.profiling_tools import profile_function
from pid_provider import exceptions


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
        if v3 := self.xml_adapter.v3:
            q |= Q(v3=v3) | Q(other_pid__pid_in_xml=v3)
        
        # PID v2
        if v2 := self.xml_adapter.v2:
            q |= Q(v2=v2) | Q(other_pid__pid_in_xml=v2) | Q(aop_pid=v2)
        
        if aop_pid := self.xml_adapter.aop_pid:
            q |= Q(v2=aop_pid) | Q(other_pid__pid_in_xml=aop_pid) | Q(aop_pid=aop_pid)
            
        # Package name
        if pkg_name := self.xml_adapter.pkg_name:
            q |= Q(pkg_name=pkg_name)

        if main_doi := self.xml_adapter.main_doi:
            q |= Q(main_doi=main_doi)

        return q
    
    @cached_property
    def issn_query(self):
        """
        Constrói query base para busca por ISSN (eletrônico ou impresso).
        
        Returns
        -------
        Q
            Query object combinando ISSN eletrônico e impresso com operador OR
        """
        q = Q()
        journal_issn_electronic = self.xml_adapter.journal_issn_electronic
        journal_issn_print = self.xml_adapter.journal_issn_print
        if not journal_issn_electronic and not journal_issn_print:
            raise exceptions.RequiredISSNErrorToGetPidProviderXMLError(
                _("Required Print or Electronic ISSN to identify XML {}").format(
                    self.xml_adapter.pkg_name,
                )
            )
        if journal_issn_electronic:
            q |= Q(issn_electronic=journal_issn_electronic)
        
        if journal_issn_print:
            q |= Q(issn_print=journal_issn_print)
        
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
        return {
            "elocation_id": self.xml_adapter.elocation_id,
            "fpage": self.xml_adapter.fpage,
            "fpage_seq": self.xml_adapter.fpage_seq,
            "lpage": self.xml_adapter.lpage,
            "pub_year": self.xml_adapter.pub_year,
            "volume": self.xml_adapter.volume,
            "number": self.xml_adapter.number,
            "suppl": self.xml_adapter.suppl,
        }
    
    @cached_property
    def article_data_query(self):
        """
        Constrói query para busca por dados textuais do artigo.
        
        Combina buscas por sobrenomes de autores, colaborações,
        links e conteúdo parcial do corpo do artigo.
        
        Returns
        -------
        Q
            Query object combinando z_surnames, z_collab, z_links e z_partial_body
        """
        if not any(
            [
                self.xml_adapter.z_surnames,
                self.xml_adapter.z_collab,
                self.xml_adapter.z_links,
                self.xml_adapter.z_partial_body,
            ]
        ):
            return None
        q = Q()
        q |= Q(z_surnames=self.xml_adapter.z_surnames)
        q |= Q(z_collab=self.xml_adapter.z_collab)
        q |= Q(z_links=self.xml_adapter.z_links)
        q |= Q(z_partial_body=self.xml_adapter.z_partial_body)
        return q