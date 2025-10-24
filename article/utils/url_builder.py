from urllib.parse import urlencode


class ArticleURLBuilder:
    """
    Classe para gerenciar a geração de URLs de artigos científicos.
    
    Attributes:
        domain: Domínio base do SciELO
        journal_acron: Acrônimo do periódico
        pid_v2: Identificador persistente versão 2 (formato clássico)
        pid_v3: Identificador persistente versão 3 (formato novo)
    """
    
    def __init__(self, domain, journal_acron, pid_v2=None, pid_v3=None):
        self.domain = domain.rstrip('/')
        if not self.domain.startswith("http"):
            self.domain = f"https://{self.domain}"
        self.journal_acron = journal_acron
        self.pid_v2 = pid_v2
        self.pid_v3 = pid_v3
    
    def set_pids(self, pid_v2=None, pid_v3=None):
        """
        Atualiza os PIDs do artigo.
        
        Args:
            pid_v2: Novo valor para pid_v2
            pid_v3: Novo valor para pid_v3
        """
        if pid_v2 is not None:
            self.pid_v2 = pid_v2
        if pid_v3 is not None:
            self.pid_v3 = pid_v3
    
    def _build_new_url(self, fmt=None, lang=None):
        """
        Gera URL do site novo para qualquer formato.
        
        Args:
            fmt: Formato desejado (html, pdf, xml)
            lang: Idioma do documento
            
        Returns:
            URL completa ou None se pid_v3 não estiver definido
        """
        if not self.pid_v3:
            return None
            
        base_url = f"{self.domain}/j/{self.journal_acron}/a/{self.pid_v3}/"
        
        params = {}
        if fmt:
            params["format"] = fmt
        if lang:
            params["lang"] = lang
        
        if params:
            return f"{base_url}?{urlencode(params)}"
        return base_url
    
    def _build_classic_url(self, fmt=None, lang=None):
        """
        Gera URL do site clássico.
        
        Args:
            fmt: Formato desejado (html, pdf)
            lang: Idioma do documento
            
        Returns:
            URL completa ou None se pid_v2 não estiver definido ou formato inválido
        """
        if not self.pid_v2:
            return None
            
        script_map = {
            "html": "sci_arttext",
            "pdf": "sci_pdf"
        }
        
        script = script_map.get(fmt)
        if not script:
            return None
            
        params = {
            "script": script,
            "pid": self.pid_v2
        }
        
        if lang:
            params["tlng"] = lang
            
        return f"{self.domain}/scielo.php?{urlencode(params)}"
    
    def get_pdf_urls(self, languages):
        """
        Gera URLs para PDFs em múltiplos idiomas.
        
        Args:
            languages: Lista de códigos de idioma
            
        Yields:
            Dicionário com 'lang' e 'url' para cada idioma
        """
        # Prioriza URLs do novo formato se pid_v3 existir
        if self.pid_v3:
            for lang in languages:
                url = self._build_new_url("pdf", lang)
                if url:
                    yield {"lang": lang, "url": url}
        
        if self.pid_v2:
            for lang in languages:
                url = self._build_classic_url("pdf", lang)
                if url:
                    yield {"lang": lang, "url": url}

    def get_html_urls(self, languages):
        """
        Gera URLs para HTMLs em múltiplos idiomas.
        
        Args:
            languages: Lista de códigos de idioma
            
        Yields:
            Dicionário com 'lang' e 'url' para cada idioma
        """
        # Prioriza URLs do novo formato se pid_v3 existir
        if self.pid_v3:
            for lang in languages:
                url = self._build_new_url("html", lang)
                if url:
                    yield {"lang": lang, "url": url}
        
        # Fallback para URLs clássicas se pid_v2 existir
        if self.pid_v2:
            for lang in languages:
                url = self._build_classic_url("html", lang)
                if url:
                    yield {"lang": lang, "url": url}

    def get_xml_url(self):
        """
        Gera URL para o XML do artigo.
        
        Returns:
            URL do XML ou None se pid_v3 não estiver definido
        """
        return self._build_new_url("xml")
    
    def get_urls(self, languages=None):
        """
        Gera todas as URLs disponíveis para o artigo.
        
        Args:
            languages: Lista de idiomas (padrão: ['pt', 'en', 'es'])
            
        Yields:
            Dicionário com 'format', 'url' e opcionalmente 'lang'
        """
        if languages is None:
            languages = ['pt', 'en', 'es']
        
        # URL do XML (apenas para pid_v3)
        xml_url = self.get_xml_url()
        if xml_url:
            yield {"format": "xml", "url": xml_url}
        
        # URLs HTML
        for item in self.get_html_urls(languages):
            yield {"format": "html", **item}
        
        # URLs PDF
        for item in self.get_pdf_urls(languages):
            yield {"format": "pdf", **item}
    
    def __repr__(self):
        return (
            f"ArticleURLBuilder(domain='{self.domain}', "
            f"journal_acron='{self.journal_acron}', "
            f"pid_v2='{self.pid_v2}', pid_v3='{self.pid_v3}')"
        )


# Exemplo de uso
if __name__ == "__main__":
    # Criando builder com PIDs
    builder = ArticleURLBuilder(
        domain="https://www.scielo.br",
        journal_acron="rbcs",
        pid_v2="S0100-06832024000100501",
        pid_v3="XYZ123"
    )
    
    # Gerando todas as URLs
    print("Todas as URLs disponíveis:")
    for url_info in builder.get_urls(languages=["pt", "en"]):
        print(f"  {url_info}")
    
    # Atualizando PIDs
    builder.set_pids(pid_v3="ABC456")
    
    # Gerando URL específica
    print(f"\nURL XML: {builder.get_xml_url()}")
    
    # Criando builder sem PIDs iniciais
    builder2 = ArticleURLBuilder(
        domain="https://www.scielo.br",
        journal_acron="rbcs"
    )
    builder2.set_pids(pid_v2="S0100-06832024000100502")
    
    print(f"\nBuilder 2 - URLs PDF:")
    for url_info in builder2.get_pdf_urls(["pt"]):
        print(f"  {url_info}")