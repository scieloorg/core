import logging

from django.contrib.auth import authenticate, login
from django.core.files.storage import FileSystemStorage
from rest_framework import status
from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
    TokenAuthentication,
)
from rest_framework.exceptions import ParseError
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.parsers import FileUploadParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from pid_provider import controller, models
from pid_provider.api.serializers import PidProviderXMLSerializer


class PidProviderViewSet(
    GenericViewSet,  # generic view functionality
    CreateModelMixin,  # handles POSTs
    RetrieveModelMixin,  # handles GETs for 1 Company
    ListModelMixin,
):  # handles GETs for many Companies

    parser_classes = (FileUploadParser,)
    http_method_names = ["post", "get", "head"]

    authentication_classes = [
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    ]
    permission_classes = [IsAuthenticated]
    queryset = models.PidProviderXML.objects.all()

    @property
    def pid_provider(self):
        if not hasattr(self, "_pid_provider") or not self._pid_provider:
            self._pid_provider = controller.PidProvider("pid-provider")
        return self._pid_provider

    def _authenticate(self, request):
        logging.info("_authenticate %s" % request.data)
        try:
            username = request.data["username"]
            password = request.data["password"]
        except:
            pass
        try:
            logging.info(request.headers)
        except:
            pass

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

    def list(self, request, pk=None):
        """
        List items filtered by from_date, issn, pub_year

        Return
        ------
            list of dict
        """
        from_ingress_date = request.query_params.get("from_ingress_date")
        include_has_article = request.query_params.get("include_has_article")
        issn = request.query_params.get("issn")
        pub_year = request.query_params.get("pub_year")
        queryset = models.PidProviderXML.xml_feed(
            from_ingress_date,
            issn,
            pub_year,
            include_has_article,
        )
        serializer = PidProviderXMLSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, format="zip"):
        """
        Receive a zip file which contains XML file(s)
        Register / Update XML data and files

        curl -X POST -S \
            -H "Content-Disposition: attachment;filename=pacote_xml.zip" \
            -F "file=@pacote_xml.zip;type=application/zip" \
            --user "adm:adm" \
            127.0.0.1:8000/pid_provider/ --output output.txt

        Return
        ------
            list of dict
                {
                    "v3": self.v3,
                    "v2": self.v2,
                    "aop_pid": self.aop_pid,
                    "xml_uri": self.xml_uri,
                    "article": self.article,
                    "created": self.created.isoformat(),
                    "updated": self.updated.isoformat(),
                    "xml_changed": boolean,
                    "record_status": created | updated | retrieved
                }
                or
                {
                    "error_type": self.error_type,
                    "error_message": self.error_message,
                    "id": self.finger_print,
                    "basename": self.basename,
                }        """

        # self._authenticate(request)
        logging.info("Receiving files %s" % request.FILES)
        logging.info("Receiving data %s" % request.data)

        uploaded_file = request.FILES["file"]
        logging.info("Receiving file name %s" % uploaded_file.name)

        fs = FileSystemStorage()
        downloaded_file = fs.save(uploaded_file.name, uploaded_file)
        downloaded_file_path = fs.path(downloaded_file)

        logging.info("Receiving temp %s" % downloaded_file_path)
        results = self.pid_provider.provide_pid_for_xml_zip(
            zip_xml_file_path=downloaded_file_path,
            user=request.user,
        )
        results = list(results)
        for item in results:
            if item.get("record_status") == "created":
                return Response(results, status=status.HTTP_201_CREATED)
            if item.get("error_type"):
                return Response(results, status=status.HTTP_400_BAD_REQUEST)
            return Response(results, status=status.HTTP_200_OK)
