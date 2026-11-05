import logging

from django.utils import timezone
from pid_provider.models import PidProviderXML
from rest_framework import status as rest_framework_status
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from article import models
from article.sources.xmlsps import load_article

from .serializers import ArticleSerializer, PublishArticleSerializer


class ArticleViewSet(viewsets.ModelViewSet):
    serializer_class = ArticleSerializer
    http_method_names = ["get"]
    queryset = models.Article.objects.all()

    def get_queryset(self):
        queryset = models.Article.objects.all()
        doi_prefix = self.request.query_params.get("doi_prefix", None)
        if doi_prefix is not None:
            queryset = queryset.filter(doi__value__startswith=doi_prefix)
        return queryset


class PublishArticleViewSet(GenericViewSet):
    """
    Registra a publicação de um artigo a partir de um PidProviderXML existente.

    Usado após o upload do XML via ``pid_provider`` para criar ou atualizar o
    ``Article`` no Core e marcá-lo como público.
    """

    http_method_names = [
        "post",
    ]
    permission_classes = [IsAuthenticated]
    serializer_class = PublishArticleSerializer

    def create(self, request):
        """
        Registra que um artigo identificado pelo PID Provider foi publicado ou
        atualizado no site público.

        Localiza o ``PidProviderXML`` pelo par ``pid_v3`` + ``sps_pkg_name``,
        carrega os metadados do XML SPS versionado, cria ou atualiza o
        ``Article`` e executa ``check_availability`` para expor o registro.

        Parameters
        ----------
        pid_v3 : str, required
            PID v3 do artigo (23 caracteres).
        sps_pkg_name : str, required
            Nome do pacote SPS associado ao XML (ex. ``2236-8906-hoehnea-49-e1082020``).

        # solicita token
        curl -X POST http://localhost:8000/api/v2/auth/token/ \
          -d 'username=scms-upload&password=secret'

        # resposta
        ```
        {"refresh":"eyJhbGciOi...","access":"eyJhbGciOi..."}
        ```

        # registra publicação do artigo
        curl -X POST http://localhost:8000/api/v1/publish_article/ \
          -H 'Authorization: Bearer eyJhbGciOi...' \
          -H 'Content-Type: application/json' \
          -d '{
            "pid_v3": "67CrZnsyZLpV7dyR7dgp6Vt",
            "sps_pkg_name": "2236-8906-hoehnea-49-e1082020"
          }'

        Return
        ------
        dict
            Resposta de sucesso (``201 Created`` para criação, ``200 OK`` para atualização)::

                {
                  "article_id": 123,
                  "pid_v3": "67CrZnsyZLpV7dyR7dgp6Vt",
                  "sps_pkg_name": "2236-8906-hoehnea-49-e1082020",
                  "operation": "created",
                  "data_status": "PUBLIC",
                  "is_public": true,
                  "timestamp": "2026-06-23T15:00:00+00:00"
                }

        Errors
        ------
        - ``400 Bad Request``: ``pid_v3`` ou ``sps_pkg_name`` ausente, vazio ou inválido.
        - ``500 Internal Server Error``: falha inesperada ao converter o XML em ``Article``.
        - ``401 Unauthorized``: token JWT ausente, expirado ou inválido.
        - ``404 Not Found``: nenhum ``PidProviderXML`` para o par informado.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifiers = serializer.validated_data

        try:
            pp_xml = self.get_pid_provider_xml(identifiers)
        except PidProviderXML.DoesNotExist:
            return Response(
                {
                    "error": "PidProviderXML not found",
                    "pid_v3": identifiers["pid_v3"],
                    "sps_pkg_name": identifiers["sps_pkg_name"],
                },
                status=rest_framework_status.HTTP_404_NOT_FOUND,
            )

        try:
            result = self.publish_article_from_pid_provider_xml(request.user, pp_xml)
        except Exception as e:
            logging.error(
                f"Erro ao registrar artigo. Identificadores: {identifiers}. Exceção: {type(e).__name__}: {e}",
                exc_info=True,
            )
            return Response(
                {
                    "error_type": str(type(e)),
                    "error_message": str(e),
                },
                status=rest_framework_status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        timestamp = timezone.now().isoformat()
        logging.info(
            f"Publish article operation={result['operation']} "
            f"pid_v3={identifiers['pid_v3']} "
            f"sps_pkg_name={identifiers['sps_pkg_name']} "
            f"article_id={result['article_id']} "
            f"user={request.user.username} timestamp={timestamp}"
        )
        return Response(
            data=self.build_response_data(result, timestamp),
            status=self.get_response_status(result),
        )

    def get_pid_provider_xml(self, identifiers):
        return PidProviderXML.objects.select_related("current_version").get(
            v3=identifiers["pid_v3"],
            pkg_name=identifiers["sps_pkg_name"],
        )

    def build_response(self, data, status=rest_framework_status.HTTP_400_BAD_REQUEST):
        return Response(data, status=status)

    def get_response_status(self, result):
        if result["operation"] == "created":
            return rest_framework_status.HTTP_201_CREATED
        return rest_framework_status.HTTP_200_OK

    def build_response_data(self, result, timestamp):
        return {key: value for key, value in result.items() if key != "article"} | {
            "timestamp": timestamp,
        }

    def publish_article_from_pid_provider_xml(self, user, pp_xml):
        operation = (
            "updated"
            if models.Article.get_by_pid_v3_or_by_sps_pkg_name(
                pid_v3=pp_xml.v3,
                sps_pkg_name=pp_xml.pkg_name,
            ).exists()
            else "created"
        )
        article = load_article(user, pp_xml=pp_xml)
        pp_xml.collections.set(article.collections)

        article.check_availability(user)

        return {
            "article": article,
            "article_id": article.id,
            "pid_v3": article.pid_v3,
            "sps_pkg_name": article.sps_pkg_name,
            "operation": operation,
            "data_status": article.data_status,
            "is_public": article.is_public,
        }
