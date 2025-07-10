from rest_framework.exceptions import ValidationError

from django.db.models import Q
from rest_framework import viewsets

from article import models
from core.validators import validate_params
from .serializers import IssueSerializer


class GenericIssueViewSet(viewsets.ModelViewSet):
    serializer_class = IssueSerializer
    http_method_names = ["get"]
    queryset = models.Issue.objects.all()


class IssueViewSet(GenericIssueViewSet):
    def get_queryset(self):
        """
        from_publication_date e until_publication_date:
            parâmetros que recuperam registros baseados no ano de publicação do periódico.

        from_date e until_date:
            parâmetros que recuperam registros a partir da data de atualização do periódico. 
            Importante para recuperar registros mais recentes.
        """
        query_params = self.request.query_params
        
        validate_params(
            self.request, 
            "collection",
            "from_publication_year",
            "until_publication_year",
            "from_date_created",
            "until_date_created",
            "from_date_updated",
            "until_date_updated",
            "issn_print",
            "issn_electronic",  
            "volume", 
            "number",
            "supplement",
            "page",
            "markup_done",
            "",
        )
        queryset = super().get_queryset()

        if collection := query_params.get("collection"):
            queryset = queryset.filter(journal__scielojournal__collection__acron3=collection)
        if from_publication_year := query_params.get("from_publication_year"):
            queryset = queryset.filter(year__gte=from_publication_year)
        if until_publication_year := query_params.get("until_publication_year"):
            queryset = queryset.filter(year__lte=until_publication_year)
        if from_date_created := query_params.get("from_date_created"):
            queryset = queryset.filter(created__gte=from_date_created.replace("/", "-"))
        if until_date_created := query_params.get("until_date_created"):
            queryset = queryset.filter(created__lte=until_date_created.replace("/", "-"))
        if from_date_updated := query_params.get("from_date_updated"):
            queryset = queryset.filter(updated__gte=from_date_updated.replace("/", "-"))
        if until_date_updated := query_params.get("until_date_updated"):
            queryset = queryset.filter(updated__lte=until_date_updated.replace("/", "-"))
        if issn_print := query_params.get("issn_print"):
            queryset = queryset.filter(journal__official__issn_print=issn_print)
        if issn_electronic := query_params.get("issn_electronic"):
            queryset = queryset.filter(journal__official__issn_electronic=issn_electronic)
        if volume := query_params.get("volume"):
            queryset = queryset.filter(volume=volume)
        if number := query_params.get("number"):
            queryset = queryset.filter(number=number)
        if supplement := query_params.get("supplement"):
            queryset = queryset.filter(supplement=supplement)
        if markup_done := query_params.get("markup_done"):
            queryset = queryset.filter(markup_done=markup_done)

        return queryset 

    