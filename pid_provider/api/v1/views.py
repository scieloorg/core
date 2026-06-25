import logging
import os
import sys
from tempfile import NamedTemporaryFile, TemporaryDirectory

from article.models import Article
from article.sources.xmlsps import load_article
from celery.exceptions import TimeoutError
from config.settings.base import RUN_ASYNC, TASK_EXPIRES, TASK_TIMEOUT
from core.utils.profiling_tools import (
    profile_endpoint,
    profile_method,
)  # ajuste o import conforme sua estrutura
from django.utils import timezone
from pid_provider.models import PidProviderXML
from pid_provider.provider import PidProvider
from pid_provider.tasks import (
    task_delete_provide_pid_tmp_zip,
    task_provide_pid_for_xml_zip,
)
from rest_framework import serializers
from rest_framework import status as rest_framework_status
from rest_framework.mixins import CreateModelMixin
from rest_framework.parsers import FileUploadParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from tracker.models import UnexpectedEvent

STATUS_MAPPING = {
    "created": rest_framework_status.HTTP_201_CREATED,
    "updated": rest_framework_status.HTTP_200_OK,
    "processing": rest_framework_status.HTTP_202_ACCEPTED,
}
# usando redis 0 maior prioridade
TASK_HIGH_PRIORITY = 0
TASK_LOW_PRIORITY = 9
# queue=queue          # Fila específica
# TASK_QUEUE = "pid_provider"


class PublishedArticleRegistrationSerializer(serializers.Serializer):
    pid_v3 = serializers.CharField(
        required=True, allow_blank=False, max_length=23, min_length=23
    )
    sps_pkg_name = serializers.CharField(
        required=True, allow_blank=False, max_length=100
    )


class PidProviderViewSet(
    GenericViewSet,  # generic view functionality
    CreateModelMixin,  # handles POSTs
):
    parser_classes = (FileUploadParser,)
    http_method_names = [
        "post",
    ]
    permission_classes = [IsAuthenticated]

    @profile_endpoint
    def create(self, request):
        """
        Receive a zip file which contains XML file(s)
        Register / Update XML data and files

        # solicita token
        curl -X POST http://localhost:8000/api/v2/auth/token/ --data 'username=adm&password=x'

        # resposta
        ```
        {"refresh":"eyJhbGx...","access":"eyJhbGc..."}
        ```
        # solicita pid v3
        curl -X POST -S \
            -H "Content-Disposition: attachment;filename=pacote_xml.zip" \
            -F "file=@path/pacote_xml.zip;type=application/zip" \
            -H 'Authorization: Bearer eyJhbGc...' \
            http://localhost:8000/api/v2/pid/pid_provider/

        Return
        ------
        list of dict
            [{"v3":"67CrZnsyZLpV7dyR7dgp6Vt",
            "v2":"S2236-89062022071116149",
            "aop_pid":null,
            "pkg_name":"2236-8906-hoehnea-49-e1082020",
            "created":"2023-07-11T22:55:49.970261+00:00",
            "updated":"2023-07-12T13:11:57.395041+00:00",
            "record_status":"updated",
            "xml_changed":true,
            "xml": "<article .../>",
            "filename":"2236-8906-hoehnea-49-e1082020.xml"}]
            or
            [{"error_msg":"Unable to provide pid for /app/core/media/teste_bPFMzbo.zip Unable to get xml items from zip file /app/core/media/teste_bPFMzbo.zip: <class 'TypeError'> /app/core/media/teste_bPFMzbo.zip has no XML. Found files: ['tr.txt']",
            "error_type":"<class 'xmlsps.xml_sps_lib.GetXMLItemsFromZipFileError'>"}]
       """

        # self._authenticate(request)
        try:
            result_status = None
            uploaded_file = request.FILES["file"]
            logging.info(f"Receiving {uploaded_file.name}")
            user = self.request.user

            if RUN_ASYNC:
                logging.info("Async")
                result = self.run_async(user, uploaded_file)
            else:
                logging.info("Sync")
                result = self.run_sync(user, uploaded_file)

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "task": "PidProviderViewSet.create",
                    "detail": dict(
                        uploaded_file=uploaded_file.name,
                    ),
                },
            )
            result = {"error_type": str(type(e)), "error_message": str(e)}
        finally:
            logging.info(result)
            if result.get("error_type"):
                result_status = rest_framework_status.HTTP_400_BAD_REQUEST
            else:
                result_status = STATUS_MAPPING.get(result.get("record_status"))
            return Response([result], status=result_status or rest_framework_status.HTTP_200_OK)

    @profile_method
    def run_async(self, user, uploaded_file):
        try:
            with NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip_file:
                for chunk in uploaded_file.chunks():
                    tmp_zip_file.write(chunk)
                    # tmp_zip_file.write(uploaded_file.read())
                temp_file_path = tmp_zip_file.name

            # 1. ENVIAR TASK com priority e expires
            response = task_provide_pid_for_xml_zip.apply_async(
                kwargs={
                    "username": user.username,
                    "user_id": user.id,
                    "zip_filename": temp_file_path,
                },
                priority=TASK_HIGH_PRIORITY,
                expires=TASK_EXPIRES,
                # queue=queue,
            )
            try:
                result = response.get(timeout=TASK_TIMEOUT)  # Espera no máximo X segundos
            except TimeoutError:
                # Timeout atingido - task ainda está rodando
                result = {
                    "record_status": "processing",
                    "task_id": response.id,
                    "message": f"Processing with {TASK_HIGH_PRIORITY} priority. Check back later.",
                    "priority": TASK_HIGH_PRIORITY,
                    "expires_in": f"{TASK_EXPIRES} seconds",
                }

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "task": "PidProviderViewSet.run_async",
                    "detail": dict(
                        uploaded_file=uploaded_file.name,
                    ),
                },
            )
            result = {"error_type": str(type(e)), "error_message": str(e)}
        finally:
            task_delete_provide_pid_tmp_zip.apply_async(
                kwargs={
                    "temp_file_path": temp_file_path,
                },
                priority=TASK_LOW_PRIORITY,
            )
            return result


    @profile_method
    def run_sync(self, user, uploaded_file):
        try:
            response = {}
            with TemporaryDirectory() as output_folder:
                downloaded_file_path = os.path.join(output_folder, uploaded_file.name)
                with open(downloaded_file_path, "wb") as fp:
                    for chunk in uploaded_file.chunks():
                        fp.write(chunk)
                    # fp.write(uploaded_file.read())
                pp = PidProvider()
                for response in pp.provide_pid_for_xml_zip(
                    downloaded_file_path,
                    user,
                    filename=None,
                    origin_date=None,
                    force_update=None,
                    is_published=None,
                    registered_in_core=None,
                    caller="core",
                ):
                    try:
                        response.pop("xml_with_pre")
                    except KeyError:
                        pass
            return response
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "task": "PidProviderViewSet.run_sync",
                    "detail": dict(
                        uploaded_file=uploaded_file.name,
                    ),
                },
            )
            return {"error_type": str(type(e)), "error_message": str(e)}


class FixPidV2ViewSet(
    GenericViewSet,  # generic view functionality
    CreateModelMixin,  # handles POSTs
):
    http_method_names = [
        "post",
    ]
    permission_classes = [IsAuthenticated]

    @profile_endpoint
    def create(self, request):
        """
        Receive a pid_v3 e correct_pid_v2
        Update PidProviderXML.current_version e PidProviderXML.v2

        # solicita token
        curl -X POST http://localhost:8000/api/v2/auth/token/ --data 'username=adm&password=x'

        # resposta
        ```
        {"refresh":"eyJhbGx...","access":"eyJhbGc..."}
        ```
        # solicita pid v3
        curl -X POST -S \
            -F "pid_v3=pid_v3" \
            -F "correct_pid_v2=correct_pid_v2" \
            -H 'Authorization: Bearer eyJhbGc...' \
            http://localhost:8000/api/v2/pid/fix_pid_v2/

        Return
        ------
        list of dict
            [{"v3":"67CrZnsyZLpV7dyR7dgp6Vt",
            "v2":"S2236-89062022071116149",
            "aop_pid":null,
            "pkg_name":"2236-8906-hoehnea-49-e1082020",
            "created":"2023-07-11T22:55:49.970261+00:00",
            "updated":"2023-07-12T13:11:57.395041+00:00",
            "record_status":"updated",
            "xml_changed":true,
            "xml": "<article .../>",
            "filename":"2236-8906-hoehnea-49-e1082020.xml"}]
            or
            [{"error_msg":"Unable to provide pid for /app/core/media/teste_bPFMzbo.zip Unable to get xml items from zip file /app/core/media/teste_bPFMzbo.zip: <class 'TypeError'> /app/core/media/teste_bPFMzbo.zip has no XML. Found files: ['tr.txt']",
            "error_type":"<class 'xmlsps.xml_sps_lib.GetXMLItemsFromZipFileError'>"}]
       """

        # self._authenticate(request)
        logging.info("Receiving files %s" % request.FILES)
        logging.info("Receiving data %s" % request.data)

        try:
            result = {}
            pid_v3 = request.data.get("pid_v3")
            correct_pid_v2 = request.data.get("correct_pid_v2")

            resp_status = rest_framework_status.HTTP_400_BAD_REQUEST
            if len(pid_v3 or "") == len(correct_pid_v2 or "") == 23:
                pp = PidProvider()
                result = pp.fix_pid_v2(
                    pid_v3=request.data.get("pid_v3"),
                    correct_pid_v2=request.data.get("correct_pid_v2"),
                    user=request.user,
                )
                if result.get("record_status") == "updated":
                    resp_status = rest_framework_status.HTTP_200_OK
            else:
                result = {
                    "error": "Invalid parameters",
                    "pid_v3": pid_v3,
                    "correct_pid_v2": correct_pid_v2,
                }
            return Response(result, status=resp_status)
        except Exception as e:
            logging.exception(e)
            return Response(
                {"error_type": str(type(e)), "error_message": str(e)},
                status=rest_framework_status.HTTP_400_BAD_REQUEST,
            )


class PublishedArticleRegistrationViewSet(GenericViewSet):
    http_method_names = [
        "post",
    ]
    permission_classes = [IsAuthenticated]
    serializer_class = PublishedArticleRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return self.build_response(serializer.errors)

        identifiers = serializer.validated_data
        pp_xml = self.get_pid_provider_xml(identifiers)
        if pp_xml is None:
            return self.build_response(
                data={
                    "error": "PidProviderXML not found",
                    "pid_v3": identifiers["pid_v3"],
                    "sps_pkg_name": identifiers["sps_pkg_name"],
                },
                status=rest_framework_status.HTTP_404_NOT_FOUND,
            )

        try:
            result = self.register_published_article_from_pid_provider_xml(
                request.user, pp_xml
            )
        except Exception as e:
            logging.error(
                f"Erro ao registrar artigo. Identificadores: {identifiers}. Exceção: {type(e).__name__}: {e}",
                exc_info=True,
            )
            return self.build_response(
                {
                    "error_type": str(type(e)),
                    "error_message": str(e),
                },
            )

        timestamp = timezone.now().isoformat()
        logging.info(
            f"Published article registration operation={result['operation']} "
            f"pid_v3={identifiers['pid_v3']} "
            f"sps_pkg_name={identifiers['sps_pkg_name']} "
            f"article_id={result['article_id']} "
            f"user={request.user.username} timestamp={timestamp}"
        )
        return self.build_response(
            data=self.build_response_data(result, timestamp),
            status=self.get_response_status(result),
        )

    def get_pid_provider_xml(self, identifiers):
        try:
            return PidProviderXML.objects.select_related("current_version").get(
                v3=identifiers["pid_v3"],
                pkg_name=identifiers["sps_pkg_name"],
            )
        except PidProviderXML.DoesNotExist:
            return None

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

    def register_published_article_from_pid_provider_xml(self, user, pp_xml):
        pid_v3 = pp_xml.v3
        sps_pkg_name = pp_xml.pkg_name
        operation = (
            "updated"
            if Article.get_by_pid_v3_or_by_sps_pkg_name(
                pid_v3=pid_v3,
                sps_pkg_name=sps_pkg_name,
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
