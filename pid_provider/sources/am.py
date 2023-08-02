import logging

from pid_provider.controller import PidProvider
from pid_provider.models import PidRequest, PidProviderXML


class AMHarvesting:
    # https://articlemeta.scielo.org/api/v1/article/identifiers/?limit=2&collection=mex

    """
    {
        "objects": [
            {
                "collection": "mex",
                "code": "S2007-09342012000200004",
                "processing_date": "2004-06-09"
            },
            {
                "collection": "mex",
                "code": "S2007-09342012000100003",
                "processing_date": "2004-06-09"
            }
        ],
        "meta": {
            "filter": {
                "collection": "mex",
                "processing_date": {
                    "$lte": "2023-07-26",
                    "$gte": "1900-01-01"
                }
            },
            "limit": 2,
            "offset": 0,
            "total": 102569
        }
    }
    """

    def __init__(self, collection_acron=None, from_date=None, limit=None, stop=None):
        """
        Configura a coleta

        collection_acron : str or None
        from_date : YYYY-MM-DD or None
        limit : int
            quantidade de itens para cada requisição
        stop : int
            atribuir valor para forçar a interrompção das requisições antes de coletar tudo
        """
        self._collection_acron = collection_acron
        self._limit = limit or 1000
        self._offset = 0
        self._total = None
        self._stop = stop
        self._from_date = from_date or "1900-01-01"

        collection_param = ""
        if self._collection_acron:
            collection_param = f"&collection={self._collection_acron}"
        self._base_uri = (
            f"https://articlemeta.scielo.org/api/v1/article/identifiers/?"
            f"limit={self._limit}&from={self._from_date}{collection_param}&offset="
        )

    def get_items(self, data):
        """
        Retorna geradores de itens
            {
                "collection": "mex",
                "code": "S2007-09342012000100003",
                "processing_date": "2004-06-09"
            }
        """
        self._total = data["meta"]["total"]
        for item in data["objects"]:
            yield {
                "collection_acron": item["collection"],
                "pid_v2": item["code"],
                "processing_date": item["processing_date"],
            }

    def uris(self):
        """
        Retorna geradores de URI do formato:

        https://articlemeta.scielo.org/api/v1/article/identifiers/?
        limit=1000&offset=3000&from=2010-09-01&collection=mex"

        """
        while True:
            logging.info(f"{self._stop} / {self._total}")

            uri = f"{self._base_uri}{self._offset}"
            logging.info(uri)

            yield uri

            # ajusta offset para a próxima iteração
            self._offset += self._limit

            # interrompe ou continua a iteração
            if self._total and self._total <= self._offset:
                break

            # força a interrumpção
            if self._stop and self._stop <= self._offset:
                break


def request_pid_v3(user, uri, collection_acron, pid_v2, processing_date, force_update):
    if not force_update:
        # skip update
        try:
            logging.info(f"Skip update {uri}")
            return PidProviderXML.objects.get(v2=pid_v2).data
        except PidProviderXML.DoesNotExist:
            pass

    try:
        pp = PidProvider()
        response = pp.provide_pid_for_xml_uri(
            uri,
            pid_v2 + ".xml",
            user,
            force_update=force_update,
            origin_date=processing_date,
            is_published=True,
        )
    except Exception as e:
        return PidRequest.register_failure(
            e=e,
            user=user,
            origin=uri,
        )

    try:
        pid_v3 = response["v3"]
    except KeyError:
        pid_v3 = None

    if not pid_v3:
        result_type = response.get("error_type") or response.get("result_type")
        result_msg = response.get("error_msg") or response.get("result_msg")

        # Guardar somente se houve problema
        pid_request = PidRequest.create_or_update(
            user=user,
            origin=uri,
            result_type=result_type,
            result_msg=result_msg,
        )
