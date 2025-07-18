import os
import logging
from tempfile import NamedTemporaryFile

from rest_framework import status
from rest_framework.mixins import CreateModelMixin
from rest_framework.parsers import FileUploadParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from pid_provider.tasks import task_provide_pid_for_xml_zip


STATUS_MAPPING = {
    "created": status.HTTP_201_CREATED,
    "updated": status.HTTP_200_OK,
}

class PidProviderViewSet(
    GenericViewSet,  # generic view functionality
    CreateModelMixin,  # handles POSTs
):
    parser_classes = (FileUploadParser,)
    http_method_names = [
        "post",
    ]
    permission_classes = [IsAuthenticated]

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
            temp_file_path = None
            uploaded_file = request.FILES["file"]
            logging.info(f"Receiving {uploaded_file.name}")
            user = self.request.user

            with NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip_file:
                for chunk in uploaded_file.chunks():
                    tmp_zip_file.write(chunk)
                temp_file_path = tmp_zip_file.name

            response = task_provide_pid_for_xml_zip.apply_async(
                kwargs=dict(
                    username=user.username,
                    user_id=user.id,
                    zip_filename=temp_file_path,
                ),
                timeout=300,
            )
            result = response.get()
        except Exception as e:
            logging.exception(e)
            result = {"error_type": str(type(e)), "error_message": str(e)}
        finally:
            logging.info(result)
            try:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            except Exception as exc:
                pass
            return Response(
                [result],
                status=STATUS_MAPPING.get(result.get("record_status")) or status.HTTP_400_BAD_REQUEST)


class FixPidV2ViewSet(
    GenericViewSet,  # generic view functionality
    CreateModelMixin,  # handles POSTs
):
    http_method_names = [
        "post",
    ]
    permission_classes = [IsAuthenticated]

    @property
    def pid_provider(self):
        if not hasattr(self, "_pid_provider") or not self._pid_provider:
            self._pid_provider = PidProvider()
        return self._pid_provider

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

            resp_status = status.HTTP_400_BAD_REQUEST
            if len(pid_v3 or "") == len(correct_pid_v2 or "") == 23:
                result = self.pid_provider.fix_pid_v2(
                    pid_v3=request.data.get("pid_v3"),
                    correct_pid_v2=request.data.get("correct_pid_v2"),
                    user=request.user,
                )
                if result.get("record_status") == "updated":
                    resp_status = status.HTTP_200_OK
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
                status=status.HTTP_400_BAD_REQUEST,
            )
