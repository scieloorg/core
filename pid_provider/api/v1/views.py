import logging

from django.core.files.storage import FileSystemStorage
from rest_framework import status
from rest_framework.mixins import CreateModelMixin
from rest_framework.parsers import FileUploadParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from pid_provider import controller


class PidProviderViewSet(
    GenericViewSet,  # generic view functionality
    CreateModelMixin,  # handles POSTs
):
    parser_classes = (FileUploadParser,)
    http_method_names = [
        "post",
    ]
    permission_classes = [IsAuthenticated]

    @property
    def pid_provider(self):
        if not hasattr(self, "_pid_provider") or not self._pid_provider:
            self._pid_provider = controller.PidProvider()
        return self._pid_provider

    def create(self, request, format="zip"):
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
        logging.info("Receiving files %s" % request.FILES)
        logging.info("Receiving data %s" % request.data)

        uploaded_file = request.FILES["file"]
        logging.info("Receiving file name %s" % uploaded_file.name)

        fs = FileSystemStorage()
        downloaded_file = fs.save(uploaded_file.name, uploaded_file)
        downloaded_file_path = fs.path(downloaded_file)

        logging.info("Receiving temp %s" % downloaded_file_path)
        try:
            results = self.pid_provider.provide_pid_for_xml_zip(
                zip_xml_file_path=downloaded_file_path,
                user=request.user,
            )
            results = list(results)
            resp_status = None
            for item in results:
                logging.info(item)
                try:
                    xml_with_pre = item.pop("xml_with_pre")
                    if item.get("xml_changed"):
                        item["xml"] = xml_with_pre.tostring()
                except KeyError:
                    resp_status = status.HTTP_400_BAD_REQUEST
                else:
                    if item.get("record_status") == "created":
                        resp_status = resp_status or status.HTTP_201_CREATED
                    else:
                        resp_status = resp_status or status.HTTP_200_OK
            return Response(results, status=resp_status)
        except Exception as e:
            logging.exception(e)
            return Response(
                [{"error_type": str(type(e)), "error_message": str(e)}],
                status=status.HTTP_400_BAD_REQUEST,
            )
