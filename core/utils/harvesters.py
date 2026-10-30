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
        limit: Optional[int] = None,
        timeout: int = 30,
        verify: bool = False,
        journal: Optional[str] = None,
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
        self.limit = limit or 1000
        self.timeout = timeout
        self.verify = verify
        self.journal = journal

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
                if self.journal:
                    params["issn"] = self.journal

                # Constrói URL
                url = f"{self.base_url}?{urlencode(params)}"

                logging.info(f"Fetching AM documents from: {url}")

                # Faz requisição
                response = fetch_data(url, json=True, timeout=self.timeout, verify=self.verify)

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
        domain: str = "https://www.scielo.br",
        collection_acron: str = "scl",
        from_date: Optional[str] = None,
        until_date: Optional[str] = None,
        limit: int = 100,
        timeout: int = 5,
        verify: bool = False,
        journal: Optional[str] = None,
        stop: Optional[str] = None,
    ):
        """
        Inicializa o harvester do OPAC.

        Args:
            domain: Domínio do OPAC (ex: 'www.scielo.br')
            collection_acron: Acrônimo da coleção (ex: 'scl')
            from_date: Data inicial em ISO 8601 (ex: 2024-01-31, 2024-01-31T10:30:15)
            until_date: Data final em ISO 8601 (padrão: agora, UTC, com segundos)
            limit: Número de documentos por página
            timeout: Timeout em segundos para requisições
        """
        self.domain = domain
        self.collection_acron = collection_acron
        # Datas e corte do counter_dict v2:
        # - o OPAC filtra por updated, em UTC, com begin_date <= updated <= end_date
        #   (limites inclusivos) e precisão de milissegundos (BSON);
        # - updated retorna com microssegundos (ex.: 2026-10-28T02:42:17.464000)
        #   e é guardado em ArticleSource.source_date;
        # - usar o source_date de uma coleta como from_date da seguinte inclui
        #   novamente o documento do limite (não há perda, só repetição);
        #   ex.: from_date=...02:42:17.464 inclui updated=...02:42:17.464000,
        #   from_date=...02:42:17.465 não inclui.
        self.from_date = from_date or "2000-01-01"
        # com hora: uma data sem hora (YYYY-MM-DD) equivale à meia-noite e
        # excluiria os documentos atualizados no próprio dia.
        # Truncada em segundos: documentos atualizados na fração de segundo
        # final ficam para a próxima coleta.
        self.until_date = until_date or datetime.utcnow().isoformat(
            timespec="seconds"
        )
        self.limit = limit or 100
        self.timeout = timeout or 5
        self.verify = verify
        self.journal = journal
        self.stop = stop

    def harvest_documents(self) -> Generator[Dict[str, Any], None, None]:
        """
        Função geradora que retorna documentos do OPAC
        (counter_dict v2: documentos ordenados por data de atualização).

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
                - origin_date: Data (YYYY-MM-DD) de atualização ou criação
                - updated: Data e hora (ISO 8601, com microssegundos) de
                  atualização ou criação
                - source_type: 'opac'
                - metadata: Metadados adicionais do documento
        """
        page = 1
        total_pages = None

        # Constrói URL
        params = {
            "begin_date": self.from_date,
            "end_date": self.until_date,
            "limit": self.limit,
        }
        if self.journal:
            params["journal"] = self.journal
        main_url = f"{self.domain}/api/v2/counter_dict?{urlencode(params)}"

        while True:
            try:
                # Constrói URL
                url = f"{main_url}&page={page}"
                logging.info(f"Fetching OPAC documents from: {url}")

                # Faz requisição
                # verify=False é necessário para evitar erros de SSL em ambientes onde o certificado do OPAC não é reconhecido
                response = fetch_data(url, json=True, timeout=self.timeout, verify=self.verify)

                # Define total de páginas na primeira iteração
                if total_pages is None:
                    total_pages = response.get("pages", 0)
                    logging.info(f"Total pages to process: {total_pages}")

                documents = response.get("documents") or []

                if not documents:
                    logging.info(f"No documents found on page {page}")
                    break

                for item in documents:
                    pid_v3 = item.get("aid") or item.get("pid_v3")
                    # Valida dados mínimos
                    if not pid_v3 or not item.get("journal_acronym"):
                        logging.warning(f"Invalid document data: {item}")
                        continue

                    # Constrói URL do XML
                    journal_acron = item["journal_acronym"]
                    xml_url = f"{self.domain}/j/{journal_acron}/a/{pid_v3}/?format=xml"

                    # Extrai data de origem
                    created = self._parse_iso_datetime(item.get("created"))
                    updated = self._parse_iso_datetime(item.get("updated")) or created
                    origin_date = updated and updated[:10]

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
                        "origin_date": origin_date,
                        "updated": updated,
                        "source_type": "opac",
                        # True ou False (v2: is_public; v1: status)
                        "is_public": (
                            item["is_public"] if "is_public" in item else item.get("status")
                        ),
                        "metadata": {
                            "aop_pid": item.get("aop_pid"),
                            "default_language": item.get("default_language"),
                            "created_at": created,
                            "updated_at": updated,
                            "origin_date": origin_date,
                            "raw_data": item,
                            "harvested_at": datetime.utcnow().isoformat(),
                        },
                    }

                    yield document

                # Verifica se deve continuar
                page += 1
                if self.stop and page > self.stop:
                    break
                if total_pages and page > total_pages:
                    logging.info(f"Completed all {total_pages} pages")
                    break

            except Exception as e:
                logging.error(f"Error harvesting OPAC documents on page {page}: {e}")
                break

    def _parse_iso_datetime(self, date_str: Optional[str]) -> Optional[str]:
        """
        Valida e normaliza data ISO 8601 retornada pelo counter_dict v2.

        Args:
            date_str: String de data ISO 8601 (ex: "2020-11-28T23:42:43.464000")

        Returns:
            Data e hora no formato ISO, com microssegundos
            (ex: "2020-11-28T23:42:43.464000") ou None se falhar
        """
        if not date_str:
            return None

        try:
            return datetime.fromisoformat(date_str).isoformat(
                timespec="microseconds"
            )
        except (ValueError, TypeError) as e:
            logging.warning(f"Failed to parse ISO date '{date_str}': {e}")
            return None

