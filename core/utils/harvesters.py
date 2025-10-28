import logging
from datetime import datetime
from typing import Any, Dict, Generator, Optional
from urllib.parse import urlencode

from core.utils.utils import fetch_data


class AMHarvester:
    """
    Harvester para coletar documentos do ArticleMeta.
    """

    def __init__(
        self,
        record_type: str,
        collection_acron: str,
        from_date: Optional[str] = None,
        until_date: Optional[str] = None,
        limit: int = 1000,
        timeout: int = 30,
    ):
        """
        Inicializa o harvester do ArticleMeta.

        Args:
            collection_acron: Acrônimo da coleção (ex: 'scl', 'mex')
            from_date: Data inicial no formato YYYY-MM-DD
            until_date: Data final no formato YYYY-MM-DD
            limit: Número de documentos por página
            timeout: Timeout em segundos para requisições
        """
        self.record_type = record_type
        self.base_url = f"https://articlemeta.scielo.org/api/v1/{self.record_type}/identifiers"
        self.collection_acron = collection_acron
        self.from_date = from_date or "1997-01-01"
        self.until_date = until_date or datetime.utcnow().isoformat()[:10]
        self.limit = limit
        self.timeout = timeout

    def harvest_documents(self) -> Generator[Dict[str, Any], None, None]:
        """
        Função geradora que retorna documentos do ArticleMeta.

        Yields:
            Dict contendo:
                - pid_v2: Identificador PID v2
                - pid_v3: Identificador PID v3 (se disponível)
                - collection_acron: Acrônimo da coleção
                - processing_date: Data de processamento
                - journal_acron: Acrônimo do periódico (se disponível)
                - publication_year: Ano de publicação (se disponível)
                - xml_url: URL para obter o XML completo
                - source_type: 'articlemeta'
                - metadata: Metadados adicionais do documento
        """
        offset = 0

        while True:
            try:
                # Monta parâmetros da requisição
                params = {
                    "collection": self.collection_acron,
                    "limit": self.limit,
                    "offset": offset,
                    "from": self.from_date,
                    "until": self.until_date,
                }

                # Constrói URL
                url = f"{self.base_url}?{urlencode(params)}"

                logging.info(f"Fetching AM documents from: {url}")

                # Faz requisição
                response = fetch_data(url, json=True, timeout=self.timeout, verify=True)

                # Processa objetos retornados
                objects = response.get("objects", [])

                if not objects:
                    logging.info(
                        f"No more documents found for collection {self.collection_acron}"
                    )
                    break

                for item in objects:
                    # Extrai dados básicos
                    pid_v2 = item.get("code")
                    if not pid_v2:
                        logging.warning(f"Document without PID v2: {item}")
                        continue

                    logging.info(item)
                    # Constrói URL do XML
                    format_param = ""
                    if self.record_type == "article":
                        format_param = "&format=xmlrsps"
                    url = (
                        f"https://articlemeta.scielo.org/api/v1/{self.record_type}?"
                        f"collection={self.collection_acron}&code={pid_v2}{format_param}"
                    )

                    # Monta dicionário padronizado
                    document = {
                        "code": pid_v2,
                        "collection": self.collection_acron,
                        "pid_v2": pid_v2,
                        "pid_v3": item.get("pid_v3"),  # Pode não existir no AM
                        "collection_acron": self.collection_acron,
                        "processing_date": item.get("processing_date"),
                        "journal_acron": item.get("journal_acronym"),
                        "publication_year": item.get("processing_year"),
                        "url": url,
                        "source_type": "articlemeta",
                        "metadata": {
                            "raw_data": item,
                            "harvested_at": datetime.utcnow().isoformat(),
                        },
                    }

                    yield document

                offset += self.limit

            except Exception as e:
                logging.error(f"Error harvesting AM documents: {e}")
                break

    def _extract_year(self, date_str: Optional[str]) -> Optional[str]:
        """Extrai o ano de uma string de data."""
        if date_str and len(date_str) >= 4:
            return date_str[:4]
        return None


class OPACHarvester:
    """
    Harvester para coletar documentos do OPAC.
    """

    def __init__(
        self,
        domain: str = "www.scielo.br",
        collection_acron: str = "scl",
        from_date: Optional[str] = None,
        until_date: Optional[str] = None,
        limit: int = 100,
        timeout: int = 5,
    ):
        """
        Inicializa o harvester do OPAC.

        Args:
            domain: Domínio do OPAC (ex: 'www.scielo.br')
            collection_acron: Acrônimo da coleção (ex: 'scl')
            from_date: Data inicial no formato YYYY-MM-DD
            until_date: Data final no formato YYYY-MM-DD
            limit: Número de documentos por página
            timeout: Timeout em segundos para requisições
        """
        self.domain = domain
        self.collection_acron = collection_acron
        self.from_date = from_date or "2000-01-01"
        self.until_date = until_date or datetime.utcnow().isoformat()[:10]
        self.limit = limit
        self.timeout = timeout

    def harvest_documents(self) -> Generator[Dict[str, Any], None, None]:
        """
        Função geradora que retorna documentos do OPAC.

        Yields:
            Dict contendo:
                - pid_v1: Identificador PID v1
                - pid_v2: Identificador PID v2
                - pid_v3: Identificador PID v3
                - collection_acron: Acrônimo da coleção
                - journal_acron: Acrônimo do periódico
                - publication_date: Data de publicação
                - publication_year: Ano de publicação
                - xml_url: URL para obter o XML completo
                - source_type: 'opac'
                - metadata: Metadados adicionais do documento
        """
        page = 1
        total_pages = None

        while True:
            try:
                # Constrói URL
                url = (
                    f"https://{self.domain}/api/v1/counter_dict?"
                    f"end_date={self.until_date}&begin_date={self.from_date}"
                    f"&limit={self.limit}&page={page}"
                )

                logging.info(f"Fetching OPAC documents from: {url}")

                # Faz requisição
                response = fetch_data(url, json=True, timeout=self.timeout, verify=True)

                # Define total de páginas na primeira iteração
                if total_pages is None:
                    total_pages = response.get("pages", 0)
                    logging.info(f"Total pages to process: {total_pages}")

                documents = response.get("documents", {})

                if not documents:
                    logging.info(f"No documents found on page {page}")
                    break

                for pid_v3, item in documents.items():
                    # Valida dados mínimos
                    if not pid_v3 or not item.get("journal_acronym"):
                        logging.warning(f"Invalid document data: {item}")
                        continue

                    # Constrói URL do XML
                    journal_acron = item["journal_acronym"]
                    xml_url = f"https://{self.domain}/j/{journal_acron}/a/{pid_v3}/?format=xml"

                    # Extrai data de origem
                    origin_date = self._parse_gmt_date(
                        item.get("update") or item.get("create")
                    )

                    # Extrai ano de publicação
                    pub_date = item.get("publication_date", "")
                    publication_year = pub_date[:4] if len(pub_date) >= 4 else None

                    # Monta dicionário padronizado
                    document = {
                        "pid_v1": item.get("pid_v1"),
                        "pid_v2": item.get("pid_v2"),
                        "pid_v3": pid_v3,
                        "collection_acron": self.collection_acron,
                        "journal_acron": journal_acron,
                        "publication_date": pub_date,
                        "publication_year": publication_year,
                        "url": xml_url,
                        "source_type": "opac",
                        "metadata": {
                            "aop_pid": item.get("aop_pid"),
                            "default_language": item.get("default_language"),
                            "created_at": self._parse_gmt_date(item.get("create")),
                            "updated_at": self._parse_gmt_date(item.get("update")),
                            "origin_date": origin_date,
                            "raw_data": item,
                            "harvested_at": datetime.utcnow().isoformat(),
                        },
                    }

                    yield document

                # Verifica se deve continuar
                page += 1
                if total_pages and page > total_pages:
                    logging.info(f"Completed all {total_pages} pages")
                    break

            except Exception as e:
                logging.error(f"Error harvesting OPAC documents on page {page}: {e}")
                break

    def _parse_gmt_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        Converte data GMT para formato ISO.

        Args:
            date_str: String de data no formato GMT (ex: "Sat, 28 Nov 2020 23:42:43 GMT")

        Returns:
            Data no formato ISO (YYYY-MM-DD) ou None se falhar
        """
        if not date_str:
            return None

        try:
            dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
            return dt.isoformat()[:10]
        except (ValueError, TypeError) as e:
            logging.warning(f"Failed to parse GMT date '{date_str}': {e}")
            return None

